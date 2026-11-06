import uuid
from collections.abc import Sequence

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from ai_engine.retrieval.vector_retriever import RetrievedChunk
from app.models.dataset import EvaluationTestCase
from app.models.document import Document
from app.models.evaluation import EvaluationResult, EvaluationRun, MetricResult
from app.models.retrieved_context import RetrievedContext


class EvaluationRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    @property
    def db_session(self) -> Session:
        return self._session

    # -------------------------------------------------------------------------- run
    def add_run(self, run: EvaluationRun) -> EvaluationRun:
        self._session.add(run)
        self._session.flush()
        return run

    def get_run_for_user(self, user_id: uuid.UUID, run_id: uuid.UUID) -> EvaluationRun | None:
        return self._session.scalar(select(EvaluationRun).where(EvaluationRun.id == run_id, EvaluationRun.user_id == user_id))

    def get_run(self, run_id: uuid.UUID) -> EvaluationRun | None:
        """Chỉ cho tác vụ nền (id do hệ thống tạo)."""
        return self._session.get(EvaluationRun, run_id, populate_existing=True)

    def list_runs(self, user_id: uuid.UUID, *, status: str | None, dataset_version_id, limit: int, offset: int):
        conditions = [EvaluationRun.user_id == user_id]
        if status:
            conditions.append(EvaluationRun.status == status)
        if dataset_version_id:
            conditions.append(EvaluationRun.dataset_version_id == dataset_version_id)
        total = self._session.scalar(select(func.count()).select_from(EvaluationRun).where(*conditions))
        items = self._session.scalars(
            select(EvaluationRun).where(*conditions).order_by(EvaluationRun.created_at.desc(), EvaluationRun.id).limit(limit).offset(offset)
        ).all()
        return list(items), total

    def mark_unfinished_runs_failed(self, message: str) -> int:
        result = self._session.execute(
            update(EvaluationRun)
            .where(EvaluationRun.status.in_(("pending", "running")))
            .values(status="failed", error_message=message)
        )
        return result.rowcount

    # -------------------------------------------------------------------------- results
    def add_result(self, result: EvaluationResult, metrics: Sequence[MetricResult], contexts: Sequence[RetrievedChunk]) -> None:
        self._session.add(result)
        self._session.flush()
        for metric in metrics:
            metric.evaluation_result_id = result.id
        self._session.add_all(metrics)
        self._session.add_all(
            RetrievedContext(
                evaluation_result_id=result.id,
                chunk_id=chunk.chunk_id,
                rank=chunk.rank,
                score=chunk.score,
                content_snapshot=chunk.content,
                document_filename_snapshot=chunk.filename,
                page_number=chunk.page_number,
            )
            for chunk in contexts
        )
        self._session.flush()

    def add_aggregates(self, metrics: Sequence[MetricResult]) -> None:
        self._session.add_all(metrics)
        self._session.flush()

    def aggregates(self, run_id: uuid.UUID) -> list[MetricResult]:
        return list(
            self._session.scalars(
                select(MetricResult)
                .where(MetricResult.run_id == run_id, MetricResult.evaluation_result_id.is_(None))
                .order_by(MetricResult.metric_name)
            ).all()
        )

    def list_results(self, run_id: uuid.UUID, *, status: str | None, category: str | None, limit: int | None, offset: int):
        conditions = [EvaluationResult.run_id == run_id]
        if status:
            conditions.append(EvaluationResult.status == status)
        if category:
            conditions.append(EvaluationResult.category == category)
        total = self._session.scalar(select(func.count()).select_from(EvaluationResult).where(*conditions))
        query = (
            select(EvaluationResult, EvaluationTestCase)
            .join(EvaluationTestCase, EvaluationTestCase.id == EvaluationResult.test_case_id)
            .where(*conditions)
            .order_by(EvaluationResult.created_at, EvaluationResult.id)
            .offset(offset)
        )
        if limit is not None:
            query = query.limit(limit)
        return [(r, c) for r, c in self._session.execute(query).all()], total

    def metrics_for_results(self, result_ids: Sequence[uuid.UUID]) -> dict[uuid.UUID, list[MetricResult]]:
        if not result_ids:
            return {}
        grouped: dict[uuid.UUID, list[MetricResult]] = {}
        for metric in self._session.scalars(
            select(MetricResult).where(MetricResult.evaluation_result_id.in_(result_ids)).order_by(MetricResult.metric_name)
        ):
            grouped.setdefault(metric.evaluation_result_id, []).append(metric)
        return grouped

    def contexts_for_results(self, result_ids: Sequence[uuid.UUID]) -> dict[uuid.UUID, list[RetrievedContext]]:
        if not result_ids:
            return {}
        grouped: dict[uuid.UUID, list[RetrievedContext]] = {}
        for context in self._session.scalars(
            select(RetrievedContext)
            .where(RetrievedContext.evaluation_result_id.in_(result_ids))
            .order_by(RetrievedContext.evaluation_result_id, RetrievedContext.rank)
        ):
            grouped.setdefault(context.evaluation_result_id, []).append(context)
        return grouped

    # -------------------------------------------------------------------------- corpus
    def corpus_processing_configs(self, user_id: uuid.UUID) -> list[dict]:
        """Các cấu hình xử lý khác nhau của tài liệu sẵn sàng (để ghi vào môi trường và phát hiện lệch)."""
        rows = self._session.scalars(
            select(Document.processing_config).where(Document.user_id == user_id, Document.status == "ready").distinct()
        ).all()
        return [row for row in rows if row]

    def commit(self) -> None:
        self._session.commit()

    def rollback(self) -> None:
        self._session.rollback()
