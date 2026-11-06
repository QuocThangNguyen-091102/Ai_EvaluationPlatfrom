import uuid
from collections.abc import Sequence

from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.dataset import DatasetVersion, EvaluationDataset, EvaluationTestCase
from app.models.document import Document
from app.models.document_chunk import DocumentChunk


class DuplicateDatasetNameError(Exception):
    pass


class DatasetRepository:
    """Truy cập dataset, version, test case. Quyền sở hữu luôn kiểm qua evaluation_datasets.user_id."""

    def __init__(self, session: Session) -> None:
        self._session = session

    # ------------------------------------------------------------------ dataset
    def add_dataset(self, dataset: EvaluationDataset) -> EvaluationDataset:
        self._session.add(dataset)
        try:
            self._session.flush()
        except IntegrityError as error:
            self._session.rollback()
            raise DuplicateDatasetNameError(dataset.name) from error
        return dataset

    def get_dataset(self, user_id: uuid.UUID, dataset_id: uuid.UUID) -> EvaluationDataset | None:
        return self._session.scalar(
            select(EvaluationDataset).where(EvaluationDataset.id == dataset_id, EvaluationDataset.user_id == user_id)
        )

    def list_datasets(self, user_id: uuid.UUID, *, limit: int, offset: int) -> tuple[list[EvaluationDataset], int]:
        condition = EvaluationDataset.user_id == user_id
        total = self._session.scalar(select(func.count()).select_from(EvaluationDataset).where(condition))
        items = self._session.scalars(
            select(EvaluationDataset).where(condition).order_by(EvaluationDataset.created_at.desc(), EvaluationDataset.id).limit(limit).offset(offset)
        ).all()
        return list(items), total

    # ------------------------------------------------------------------ version
    def add_version(self, version: DatasetVersion) -> DatasetVersion:
        self._session.add(version)
        self._session.flush()
        return version

    def next_version_number(self, dataset_id: uuid.UUID) -> int:
        current = self._session.scalar(select(func.max(DatasetVersion.version_number)).where(DatasetVersion.dataset_id == dataset_id))
        return (current or 0) + 1

    def get_version(self, user_id: uuid.UUID, version_id: uuid.UUID) -> DatasetVersion | None:
        return self._session.scalar(
            select(DatasetVersion)
            .join(EvaluationDataset, EvaluationDataset.id == DatasetVersion.dataset_id)
            .where(DatasetVersion.id == version_id, EvaluationDataset.user_id == user_id)
        )

    def list_versions(self, dataset_id: uuid.UUID) -> list[tuple[DatasetVersion, int]]:
        rows = self._session.execute(
            select(DatasetVersion, func.count(EvaluationTestCase.id))
            .outerjoin(EvaluationTestCase, EvaluationTestCase.dataset_version_id == DatasetVersion.id)
            .where(DatasetVersion.dataset_id == dataset_id)
            .group_by(DatasetVersion.id)
            .order_by(DatasetVersion.version_number.desc())
        ).all()
        return [(version, count) for version, count in rows]

    def count_cases(self, version_id: uuid.UUID) -> int:
        return self._session.scalar(
            select(func.count()).select_from(EvaluationTestCase).where(EvaluationTestCase.dataset_version_id == version_id)
        )

    # ------------------------------------------------------------------ test case
    def list_cases(
        self, version_id: uuid.UUID, *, question_type: str | None, difficulty: str | None, limit: int | None, offset: int
    ) -> tuple[list[EvaluationTestCase], int]:
        conditions = [EvaluationTestCase.dataset_version_id == version_id]
        if question_type:
            conditions.append(EvaluationTestCase.question_type == question_type)
        if difficulty:
            conditions.append(EvaluationTestCase.difficulty == difficulty)
        total = self._session.scalar(select(func.count()).select_from(EvaluationTestCase).where(*conditions))
        query = select(EvaluationTestCase).where(*conditions).order_by(EvaluationTestCase.created_at, EvaluationTestCase.id).offset(offset)
        if limit is not None:
            query = query.limit(limit)
        return list(self._session.scalars(query).all()), total

    def get_case(self, user_id: uuid.UUID, case_id: uuid.UUID) -> tuple[EvaluationTestCase, DatasetVersion] | None:
        row = self._session.execute(
            select(EvaluationTestCase, DatasetVersion)
            .join(DatasetVersion, DatasetVersion.id == EvaluationTestCase.dataset_version_id)
            .join(EvaluationDataset, EvaluationDataset.id == DatasetVersion.dataset_id)
            .where(EvaluationTestCase.id == case_id, EvaluationDataset.user_id == user_id)
        ).first()
        return (row[0], row[1]) if row else None

    def add_cases(self, cases: Sequence[EvaluationTestCase]) -> None:
        self._session.add_all(cases)
        self._session.flush()

    def delete_case(self, case: EvaluationTestCase) -> None:
        self._session.execute(delete(EvaluationTestCase).where(EvaluationTestCase.id == case.id))

    # ------------------------------------------------------------------ tài liệu để giải câu trích
    def ready_documents_by_filename(self, user_id: uuid.UUID, filename: str) -> list[Document]:
        return list(
            self._session.scalars(
                select(Document).where(Document.user_id == user_id, Document.filename == filename, Document.status == "ready")
            ).all()
        )

    def ready_document(self, user_id: uuid.UUID, document_id: uuid.UUID) -> Document | None:
        return self._session.scalar(
            select(Document).where(Document.id == document_id, Document.user_id == user_id, Document.status == "ready")
        )

    def chunk_spans(self, user_id: uuid.UUID, document_id: uuid.UUID) -> list[tuple[int, int, str]]:
        rows = self._session.execute(
            select(DocumentChunk.char_start, DocumentChunk.char_end, DocumentChunk.content)
            .where(DocumentChunk.document_id == document_id, DocumentChunk.user_id == user_id)
            .order_by(DocumentChunk.chunk_index)
        ).all()
        return [(row.char_start, row.char_end, row.content) for row in rows]

    def flush(self) -> None:
        self._session.flush()

    def commit(self) -> None:
        self._session.commit()
