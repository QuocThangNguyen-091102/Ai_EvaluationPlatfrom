"""Benchmark (M8): chạy nhiều lượt đánh giá trên cùng dataset version, mỗi lượt một cấu hình, rồi so sánh.

Benchmark không có logic chấm riêng: mỗi biến thể là một EvaluationRun bình thường (cùng runner, cùng RAG pipeline),
nên số liệu của benchmark và của trang Đánh giá luôn khớp nhau.
"""

import logging
import uuid
from collections.abc import Callable
from contextlib import AbstractContextManager
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.models.benchmark import BenchmarkRun
from app.models.user import User
from app.repositories.benchmark_repository import BenchmarkRepository
from app.repositories.evaluation_repository import EvaluationRepository
from app.schemas.benchmark import BenchmarkCreate
from app.schemas.evaluation import EvaluationCreate
from app.services.evaluation_service import EvaluationRunService, EvaluationService
from app.services.model_config_service import ModelConfigService
from evaluation.benchmarks.benchmark_runner import config_differences, usage_stats
from evaluation.reports.report_builder import build_csv

logger = logging.getLogger(__name__)

INTERRUPTED_MESSAGE = "Benchmark bị gián đoạn vì máy chủ khởi động lại; hãy tạo benchmark mới"
COMPARED_METRICS = (
    "behavior_correct", "precision_at_k", "recall_at_k", "mrr", "ndcg_at_k", "context_precision", "context_recall",
    "faithfulness", "answer_relevancy",
)
VARIABLE_LABELS = {"llm_model": "LLM model", "top_k": "top_k", "prompt_version": "prompt version"}


def _now() -> datetime:
    return datetime.now(timezone.utc)


class BenchmarkService:
    def __init__(self, benchmarks: BenchmarkRepository, evaluations: EvaluationService, configs: ModelConfigService) -> None:
        self._benchmarks = benchmarks
        self._evaluations = evaluations
        self._configs = configs

    def create(self, user: User, payload: BenchmarkCreate) -> tuple[BenchmarkRun, list[uuid.UUID]]:
        # Kiểm tra hết điều kiện trước khi ghi gì vào DB.
        self._evaluations.require_reviewed_version(user, payload.dataset_version_id)
        configs = [self._configs.resolve_for_use(user, config_id) for config_id in payload.model_configuration_ids]
        snapshots = [{field: getattr(c, field) for field in ("llm_provider", "llm_model", "top_k", "prompt_version", "temperature", "embedding_model", "chunk_size", "chunk_overlap")} for c in configs]
        varies, others = config_differences(snapshots, payload.varied_variable)
        label = VARIABLE_LABELS[payload.varied_variable]
        if not varies:
            raise AppError(422, "validation_error", f"Các cấu hình phải có giá trị {label} khác nhau từng đôi một")
        notes = []
        if others:
            notes.append(
                f"Các cấu hình còn khác nhau ở: {', '.join(others)}. Khác biệt kết quả không thể quy hết cho {label}."
            )
        benchmark = self._benchmarks.add(
            BenchmarkRun(
                user_id=user.id,
                dataset_version_id=payload.dataset_version_id,
                name=payload.name.strip(),
                varied_variable=payload.varied_variable,
                status="pending",
                judge_model=payload.judge_model,
                notes=notes,
            )
        )
        run_ids = []
        for config in configs:
            run = self._evaluations.create_run(
                user,
                EvaluationCreate(dataset_version_id=payload.dataset_version_id, model_configuration_id=config.id, judge_model=payload.judge_model),
                benchmark_run_id=benchmark.id,
                commit=False,
            )
            run_ids.append(run.id)
        self._benchmarks.commit()
        return benchmark, run_ids

    def list_benchmarks(self, user: User, *, limit: int, offset: int):
        return self._benchmarks.list_for_user(user.id, limit=limit, offset=offset)

    def get(self, user: User, benchmark_id: uuid.UUID) -> BenchmarkRun:
        benchmark = self._benchmarks.get_for_user(user.id, benchmark_id)
        if benchmark is None:
            raise AppError(404, "not_found", "Không tìm thấy benchmark")
        return benchmark

    def variants(self, benchmark: BenchmarkRun) -> list[dict]:
        runs = self._benchmarks.child_runs(benchmark.id)
        usage = self._benchmarks.usage_for_runs([run.id for run in runs])
        aggregates = EvaluationRepository(self._benchmarks.db_session)
        result = []
        for run in runs:
            config = (run.environment or {}).get("model_configuration", {})
            result.append(
                {
                    "evaluation_run_id": run.id,
                    "model_configuration": config,
                    "varied_value": config.get(benchmark.varied_variable),
                    "status": run.status,
                    "total_cases": run.total_cases,
                    "completed_cases": run.completed_cases,
                    "failed_cases": run.failed_cases,
                    "categories": run.categories or {},
                    "aggregate_metrics": aggregates.aggregates(run.id),
                    "usage": usage_stats(usage[run.id]).as_dict(),
                    "error_message": run.error_message,
                }
            )
        return result

    def report_csv(self, user: User, benchmark_id: uuid.UUID) -> tuple[BenchmarkRun, str]:
        benchmark = self.get(user, benchmark_id)
        if benchmark.status != "completed":
            raise AppError(409, "conflict", "Chỉ xuất báo cáo khi benchmark đã hoàn tất")
        variants = self.variants(benchmark)
        metadata = [
            ("benchmark", benchmark.name),
            ("benchmark_id", benchmark.id),
            ("biến thay đổi", benchmark.varied_variable),
            ("dataset version id", benchmark.dataset_version_id),
            ("judge", benchmark.judge_model or "không dùng"),
            ("bắt đầu", benchmark.started_at),
            ("kết thúc", benchmark.finished_at),
            *[(f"ghi chú {i}", note) for i, note in enumerate(benchmark.notes or [], start=1)],
            ("lưu ý", "Chi phí là ước tính theo bảng giá trong configs/models.yaml; trống nghĩa là không biết giá, không phải miễn phí."),
        ]
        columns = [
            benchmark.varied_variable, "llm", "top_k", "prompt_version", "status", "cases", "failed_cases", *COMPARED_METRICS,
            "latency_mean_ms", "latency_p50_ms", "latency_p95_ms", "prompt_tokens", "completion_tokens", "total_cost", "cost_incomplete", "evaluation_run_id",
        ]
        rows = []
        for variant in variants:
            config = variant["model_configuration"]
            values = {m.metric_name: m.value for m in variant["aggregate_metrics"]}
            usage = variant["usage"]
            rows.append(
                {
                    benchmark.varied_variable: variant["varied_value"],
                    "llm": f"{config.get('llm_provider')}/{config.get('llm_model')}",
                    "top_k": config.get("top_k"),
                    "prompt_version": config.get("prompt_version"),
                    "status": variant["status"],
                    "cases": variant["total_cases"],
                    "failed_cases": variant["failed_cases"],
                    **{name: values.get(name) for name in COMPARED_METRICS},
                    **{key: usage[key] for key in ("latency_mean_ms", "latency_p50_ms", "latency_p95_ms", "prompt_tokens", "completion_tokens", "total_cost", "cost_incomplete")},
                    "evaluation_run_id": variant["evaluation_run_id"],
                }
            )
        return benchmark, build_csv(metadata, columns, rows)


class BenchmarkRunService:
    """Chạy tuần tự các lượt con bằng EvaluationRunService (một máy chủ nhỏ, tránh chạy song song tốn RAM)."""

    def __init__(self, *, session_factory: Callable[[], AbstractContextManager[Session]], evaluation_runner: EvaluationRunService) -> None:
        self._session_factory = session_factory
        self._evaluation_runner = evaluation_runner

    def execute(self, benchmark_id: uuid.UUID, run_ids: list[uuid.UUID]) -> None:
        with self._session_factory() as session:
            benchmarks = BenchmarkRepository(session)
            benchmark = benchmarks.get(benchmark_id)
            if benchmark is None:
                return
            benchmark.status, benchmark.started_at = "running", _now()
            benchmarks.commit()

        for run_id in run_ids:
            self._evaluation_runner.execute(run_id)

        with self._session_factory() as session:
            benchmarks = BenchmarkRepository(session)
            benchmark = benchmarks.get(benchmark_id)
            if benchmark is None:
                return
            failed = [run for run in benchmarks.child_runs(benchmark_id) if run.status != "completed"]
            if failed:
                benchmark.status = "failed"
                benchmark.error_message = f"{len(failed)} lượt đánh giá con không hoàn tất; xem từng lượt"
            else:
                benchmark.status = "completed"
            benchmark.finished_at = _now()
            benchmarks.commit()
        logger.info("Benchmark finished: id=%s failed_children=%s", benchmark_id, len(failed))

    def recover_interrupted(self) -> int:
        with self._session_factory() as session:
            benchmarks = BenchmarkRepository(session)
            count = benchmarks.mark_unfinished_failed(INTERRUPTED_MESSAGE)
            benchmarks.commit()
        return count
