"""Đánh giá RAG (M6): tạo lượt đánh giá, chạy nền qua RAG pipeline dùng chung, lưu kết quả, xuất báo cáo.

- `EvaluationService`: phục vụ request (tạo, liệt kê, xem, báo cáo), kiểm tra quyền và điều kiện.
- `EvaluationRunService`: chạy nền với session riêng; lưu từng câu ngay khi xong; phục hồi lượt dở khi khởi động lại.
"""

import logging
import uuid
from collections.abc import Callable
from contextlib import AbstractContextManager
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from ai_engine.generation.base_llm_client import LlmClient
from ai_engine.pipeline.rag_pipeline import RagPipeline
from app.core.exceptions import AppError
from app.core.run_environment import snapshot
from app.models.evaluation import EvaluationResult, EvaluationRun, MetricResult
from app.models.model_config import ModelConfiguration
from app.models.user import User
from app.repositories.dataset_repository import DatasetRepository
from app.repositories.evaluation_repository import EvaluationRepository
from app.schemas.evaluation import EvaluationCreate
from app.services.model_config_service import ModelConfigService, llm_configured
from evaluation.evaluators.judge_prompts import DEFAULT_JUDGE_PROMPT_VERSION
from evaluation.evaluators.llm_judge import LlmJudge
from evaluation.metrics.retrieval.relevance import Span
from evaluation.reports.report_builder import build_csv
from evaluation.runners.evaluation_runner import CaseInput, CaseOutcome, EvaluationRunner

logger = logging.getLogger(__name__)

INTERRUPTED_MESSAGE = "Lượt đánh giá bị gián đoạn vì máy chủ khởi động lại; hãy tạo lượt mới"
UNEXPECTED_MESSAGE = "Lỗi hệ thống khi chạy đánh giá"
REPORT_METRICS = (
    "behavior_correct", "precision_at_k", "recall_at_k", "reciprocal_rank", "ndcg_at_k", "context_precision", "context_recall",
    "faithfulness", "answer_relevancy",
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


class EvaluationService:
    def __init__(self, evaluations: EvaluationRepository, datasets: DatasetRepository, configs: ModelConfigService) -> None:
        self._evaluations = evaluations
        self._datasets = datasets
        self._configs = configs

    def create_run(
        self, user: User, payload: EvaluationCreate, *, benchmark_run_id: uuid.UUID | None = None, commit: bool = True
    ) -> EvaluationRun:
        """`commit=False`: chỉ flush, để benchmark tạo nhiều lượt con trong cùng một transaction."""
        version = self.require_reviewed_version(user, payload.dataset_version_id)
        config = self._configs.resolve_for_use(user, payload.model_configuration_id)
        if payload.judge_model and not llm_configured():
            raise AppError(422, "validation_error", "Máy chủ chưa cấu hình LLM nên không có judge; để trống judge_model")

        case_count = self._datasets.count_cases(version.id)
        corpus = self._evaluations.corpus_processing_configs(user.id)
        warnings = []
        mismatched = [c for c in corpus if c.get("chunk_size") != config.chunk_size or c.get("chunk_overlap") != config.chunk_overlap]
        if mismatched:
            warnings.append(
                "Cấu hình chunk của tài liệu khác cấu hình đánh giá; kết quả phản ánh cách chunk thực tế của tài liệu "
                "(xem corpus_processing_configs)"
            )
        run = self._evaluations.add_run(
            EvaluationRun(
                user_id=user.id,
                benchmark_run_id=benchmark_run_id,
                dataset_version_id=version.id,
                model_configuration_id=config.id,
                status="pending",
                total_cases=case_count,
                judge_model=payload.judge_model,
                judge_prompt_version=(payload.judge_prompt_version or DEFAULT_JUDGE_PROMPT_VERSION) if payload.judge_model else None,
                environment=snapshot(
                    dataset_version={"id": str(version.id), "version_number": version.version_number, "cases": case_count},
                    model_configuration=_config_snapshot(config),
                    judge={"model": payload.judge_model, "prompt_version": (payload.judge_prompt_version or DEFAULT_JUDGE_PROMPT_VERSION) if payload.judge_model else None},
                    corpus_processing_configs=corpus,
                    warnings=warnings,
                ),
            )
        )
        if commit:
            self._evaluations.commit()
        return run

    def require_reviewed_version(self, user: User, version_id: uuid.UUID):
        version = self._datasets.get_version(user.id, version_id)
        if version is None:
            raise AppError(404, "not_found", "Không tìm thấy phiên bản dataset")
        if version.status != "reviewed":
            raise AppError(409, "conflict", "Chỉ đánh giá được phiên bản dataset đã duyệt (để kết quả tái lập được)")
        return version

    def list_runs(self, user: User, **filters):
        return self._evaluations.list_runs(user.id, **filters)

    def get_run(self, user: User, run_id: uuid.UUID) -> EvaluationRun:
        run = self._evaluations.get_run_for_user(user.id, run_id)
        if run is None:
            raise AppError(404, "not_found", "Không tìm thấy lượt đánh giá")
        return run

    def aggregates(self, run: EvaluationRun) -> list[MetricResult]:
        return self._evaluations.aggregates(run.id)

    def results(self, user: User, run_id: uuid.UUID, *, status=None, category=None, limit=None, offset=0):
        run = self.get_run(user, run_id)
        rows, total = self._evaluations.list_results(run.id, status=status, category=category, limit=limit, offset=offset)
        ids = [result.id for result, _ in rows]
        return rows, total, self._evaluations.metrics_for_results(ids), self._evaluations.contexts_for_results(ids)

    def report_csv(self, user: User, run_id: uuid.UUID) -> tuple[EvaluationRun, str]:
        run = self.get_run(user, run_id)
        if run.status != "completed":
            raise AppError(409, "conflict", "Chỉ xuất báo cáo khi lượt đánh giá đã hoàn tất")
        rows, _, metrics, _ = self.results(user, run_id)
        environment = run.environment or {}
        config = environment.get("model_configuration", {})
        metadata = [
            ("run_id", run.id),
            ("trạng thái", run.status),
            ("dataset version", (environment.get("dataset_version") or {}).get("version_number")),
            ("LLM", f"{config.get('llm_provider')}/{config.get('llm_model')}"),
            ("embedding", config.get("embedding_model")),
            ("prompt", config.get("prompt_version")),
            ("top_k", config.get("top_k")),
            ("temperature", config.get("temperature")),
            ("chunk size / overlap", f"{config.get('chunk_size')} / {config.get('chunk_overlap')}"),
            ("judge", run.judge_model or "không dùng"),
            ("judge prompt", run.judge_prompt_version),
            ("số câu", run.total_cases),
            ("số câu lỗi", run.failed_cases),
            ("bắt đầu", run.started_at),
            ("kết thúc", run.finished_at),
        ]
        metadata += [(f"trung bình {m.metric_name}" + (f"@{m.k}" if m.k else ""), m.value) for m in self.aggregates(run)]
        columns = ["test_case_id", "question", "expected_behavior", "status", "category", "answer", "insufficient_context", *REPORT_METRICS, "latency_ms", "prompt_tokens", "completion_tokens", "estimated_cost", "error_message"]
        table = []
        for result, case in rows:
            values = {m.metric_name: m.value for m in metrics.get(result.id, [])}
            table.append(
                {
                    "test_case_id": case.id,
                    "question": case.question,
                    "expected_behavior": case.expected_behavior,
                    "status": result.status,
                    "category": result.category,
                    "answer": result.answer,
                    "insufficient_context": result.insufficient_context,
                    **{name: values.get(name) for name in REPORT_METRICS},
                    "latency_ms": result.latency_ms,
                    "prompt_tokens": result.prompt_tokens,
                    "completion_tokens": result.completion_tokens,
                    "estimated_cost": result.estimated_cost,
                    "error_message": result.error_message,
                }
            )
        return run, build_csv(metadata, columns, table)


class EvaluationRunService:
    def __init__(
        self,
        *,
        session_factory: Callable[[], AbstractContextManager[Session]],
        pipeline_provider: Callable[[], RagPipeline],
        judge_client_for: Callable[[str], LlmClient],
    ) -> None:
        self._session_factory = session_factory
        self._pipeline_provider = pipeline_provider
        self._judge_client_for = judge_client_for

    def execute(self, run_id: uuid.UUID) -> None:
        with self._session_factory() as session:
            evaluations = EvaluationRepository(session)
            run = evaluations.get_run(run_id)
            if run is None:
                return
            run.status, run.started_at = "running", _now()
            evaluations.commit()
            try:
                self._execute(session, evaluations, run)
            except Exception:
                logger.exception("Evaluation run failed: run_id=%s", run_id)
                evaluations.rollback()
                run = evaluations.get_run(run_id)
                if run is not None:
                    run.status, run.error_message, run.finished_at = "failed", UNEXPECTED_MESSAGE, _now()
                    evaluations.commit()

    def _execute(self, session: Session, evaluations: EvaluationRepository, run: EvaluationRun) -> None:
        config = session.get(ModelConfiguration, run.model_configuration_id)
        cases, _ = DatasetRepository(session).list_cases(run.dataset_version_id, question_type=None, difficulty=None, limit=None, offset=0)
        rag_config = ModelConfigService.to_rag_config(config)
        pipeline = self._pipeline_provider()
        judge = LlmJudge(self._judge_client_for(run.judge_model), run.judge_prompt_version) if run.judge_model else None
        run_id, user_id = run.id, run.user_id

        def ask(question: str):
            return pipeline.run(session, question=question, user_id=user_id, config=rag_config)

        def on_case(outcome: CaseOutcome) -> None:
            result = outcome.result
            evaluations.add_result(
                EvaluationResult(
                    run_id=run_id,
                    test_case_id=outcome.case_id,
                    status=outcome.status,
                    category=outcome.category,
                    answer=result.answer if result else None,
                    insufficient_context=result.insufficient_context if result else None,
                    mode=result.mode if result else None,
                    error_message=outcome.error_message,
                    latency_ms=result.latency_ms if result else None,
                    prompt_tokens=result.prompt_tokens if result else None,
                    completion_tokens=result.completion_tokens if result else None,
                    estimated_cost=result.estimated_cost if result else None,
                ),
                [_metric_row(run_id, m) for m in outcome.metrics],
                result.contexts if result else [],
            )
            current = evaluations.get_run(run_id)
            if outcome.status == "error":
                current.failed_cases += 1
            else:
                current.completed_cases += 1
            evaluations.commit()

        summary = EvaluationRunner(
            ask=ask,
            k=rag_config.top_k,
            judge=judge,
            on_case=on_case,
            judge_unavailable_reason="Lượt đánh giá không chọn judge model",
        ).run(
            [
                CaseInput(
                    case.id,
                    case.question,
                    case.expected_behavior,
                    [Span(r["document_content_hash"], r["char_start"], r["char_end"]) for r in case.reference_contexts],
                    ground_truth=case.ground_truth_answer,
                )
                for case in cases
            ]
        )
        evaluations.add_aggregates([_metric_row(run_id, m) for m in summary.aggregates])
        run = evaluations.get_run(run_id)
        run.categories = summary.categories
        run.status, run.finished_at = "completed", _now()
        evaluations.commit()
        logger.info("Evaluation run completed: run_id=%s cases=%s failed=%s", run_id, summary.total, summary.failed)

    def recover_interrupted(self) -> int:
        with self._session_factory() as session:
            evaluations = EvaluationRepository(session)
            count = evaluations.mark_unfinished_runs_failed(INTERRUPTED_MESSAGE)
            evaluations.commit()
        return count


def _metric_row(run_id: uuid.UUID, metric) -> MetricResult:
    return MetricResult(
        run_id=run_id,
        metric_name=metric.name,
        k=metric.k,
        value=metric.value if metric.status == "computed" else None,
        method=metric.method,
        status=metric.status,
        details=metric.details,
    )


def _config_snapshot(config: ModelConfiguration) -> dict:
    return {
        "id": str(config.id),
        "name": config.name,
        "llm_provider": config.llm_provider,
        "llm_model": config.llm_model,
        "embedding_provider": config.embedding_provider,
        "embedding_model": config.embedding_model,
        "prompt_version": config.prompt_version,
        "top_k": config.top_k,
        "temperature": config.temperature,
        "chunk_size": config.chunk_size,
        "chunk_overlap": config.chunk_overlap,
    }
