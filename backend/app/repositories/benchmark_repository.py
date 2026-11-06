import uuid
from collections.abc import Sequence

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.models.benchmark import BenchmarkRun
from app.models.evaluation import EvaluationResult, EvaluationRun
from evaluation.benchmarks.benchmark_runner import ResultUsage


class BenchmarkRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    @property
    def db_session(self) -> Session:
        return self._session

    def add(self, benchmark: BenchmarkRun) -> BenchmarkRun:
        self._session.add(benchmark)
        self._session.flush()
        return benchmark

    def get_for_user(self, user_id: uuid.UUID, benchmark_id: uuid.UUID) -> BenchmarkRun | None:
        return self._session.scalar(select(BenchmarkRun).where(BenchmarkRun.id == benchmark_id, BenchmarkRun.user_id == user_id))

    def get(self, benchmark_id: uuid.UUID) -> BenchmarkRun | None:
        """Chỉ cho tác vụ nền (id do hệ thống tạo)."""
        return self._session.get(BenchmarkRun, benchmark_id, populate_existing=True)

    def list_for_user(self, user_id: uuid.UUID, *, limit: int, offset: int):
        condition = BenchmarkRun.user_id == user_id
        total = self._session.scalar(select(func.count()).select_from(BenchmarkRun).where(condition))
        items = self._session.scalars(
            select(BenchmarkRun).where(condition).order_by(BenchmarkRun.created_at.desc(), BenchmarkRun.id).limit(limit).offset(offset)
        ).all()
        return list(items), total

    def child_runs(self, benchmark_id: uuid.UUID) -> list[EvaluationRun]:
        return list(
            self._session.scalars(
                select(EvaluationRun)
                .where(EvaluationRun.benchmark_run_id == benchmark_id)
                .order_by(EvaluationRun.created_at, EvaluationRun.id)
                .execution_options(populate_existing=True)
            ).all()
        )

    def usage_for_runs(self, run_ids: Sequence[uuid.UUID]) -> dict[uuid.UUID, list[ResultUsage]]:
        grouped: dict[uuid.UUID, list[ResultUsage]] = {run_id: [] for run_id in run_ids}
        if not run_ids:
            return grouped
        rows = self._session.execute(
            select(
                EvaluationResult.run_id,
                EvaluationResult.latency_ms,
                EvaluationResult.prompt_tokens,
                EvaluationResult.completion_tokens,
                EvaluationResult.estimated_cost,
                EvaluationResult.status,
            ).where(EvaluationResult.run_id.in_(run_ids))
        )
        for run_id, latency, prompt, completion, cost, status in rows:
            grouped[run_id].append(ResultUsage(latency, prompt, completion, cost, status))
        return grouped

    def mark_unfinished_failed(self, message: str) -> int:
        result = self._session.execute(
            update(BenchmarkRun)
            .where(BenchmarkRun.status.in_(("pending", "running")))
            .values(status="failed", error_message=message, finished_at=func.now())
        )
        return result.rowcount

    def commit(self) -> None:
        self._session.commit()
