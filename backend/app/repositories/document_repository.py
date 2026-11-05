import uuid

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.document_chunk import DocumentChunk


class DuplicateDocumentError(Exception):
    """Cùng user đã có document cùng nội dung (ràng buộc duy nhất bị vi phạm)."""


class DocumentRepository:
    """Nơi duy nhất truy cập bảng documents. Mọi truy vấn đều lọc theo user_id (cô lập dữ liệu)."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def find_by_hash(self, user_id: uuid.UUID, content_hash: str) -> Document | None:
        return self._session.scalar(
            select(Document).where(Document.user_id == user_id, Document.content_hash == content_hash)
        )

    def count_chunks(self, user_id: uuid.UUID, document_id: uuid.UUID) -> int:
        return self._session.scalar(
            select(func.count())
            .select_from(DocumentChunk)
            .where(DocumentChunk.user_id == user_id, DocumentChunk.document_id == document_id)
        )

    def add(self, document: Document) -> Document:
        """Thêm vào transaction hiện tại (chưa commit) để caller gom với các bước khác."""
        self._session.add(document)
        try:
            self._session.flush()
        except IntegrityError as exc:
            self._session.rollback()
            raise DuplicateDocumentError(document.content_hash) from exc
        return document

    def commit(self) -> None:
        self._session.commit()

    def rollback(self) -> None:
        self._session.rollback()

    def refresh(self, document: Document) -> None:
        self._session.refresh(document)
