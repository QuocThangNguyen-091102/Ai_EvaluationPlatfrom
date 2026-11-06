import uuid
from typing import Any

from sqlalchemy import delete, func, select, update
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

    def get_for_user(self, user_id: uuid.UUID, document_id: uuid.UUID) -> Document | None:
        """Trả None cả khi document tồn tại nhưng thuộc user khác (caller trả 404, không lộ sự tồn tại)."""
        return self._session.scalar(select(Document).where(Document.id == document_id, Document.user_id == user_id))

    def list_for_user(
        self, user_id: uuid.UUID, *, status: str | None, limit: int, offset: int
    ) -> tuple[list[tuple[Document, int]], int]:
        """Trả (danh sách (document, số chunk), tổng số), mới nhất trước."""
        conditions = [Document.user_id == user_id]
        if status is not None:
            conditions.append(Document.status == status)

        total = self._session.scalar(select(func.count()).select_from(Document).where(*conditions))
        rows = self._session.execute(
            select(Document, func.count(DocumentChunk.id))
            .outerjoin(
                DocumentChunk,
                (DocumentChunk.document_id == Document.id) & (DocumentChunk.user_id == Document.user_id),
            )
            .where(*conditions)
            .group_by(Document.id)
            .order_by(Document.created_at.desc(), Document.id)
            .limit(limit)
            .offset(offset)
        ).all()
        return [(document, chunk_count) for document, chunk_count in rows], total

    def get_by_id(self, document_id: uuid.UUID) -> Document | None:
        """Chỉ dùng cho tác vụ nền đã biết document_id do chính hệ thống tạo; request của user dùng get_for_user."""
        return self._session.get(Document, document_id, populate_existing=True)

    def set_status(
        self,
        document: Document,
        status: str,
        *,
        error_message: str | None = None,
        processing_config: dict[str, Any] | None = None,
    ) -> None:
        document.status = status
        document.error_message = error_message
        if processing_config is not None:
            document.processing_config = processing_config
        self._session.flush()

    def mark_unfinished_as_failed(self, message: str) -> int:
        result = self._session.execute(
            update(Document)
            .where(Document.status.in_(("uploaded", "processing")))
            .values(status="failed", error_message=message)
        )
        return result.rowcount

    def find_by_hash(self, user_id: uuid.UUID, content_hash: str) -> Document | None:
        return self._session.scalar(
            select(Document).where(Document.user_id == user_id, Document.content_hash == content_hash)
        )

    def count_for_user(self, user_id: uuid.UUID) -> int:
        return self._session.scalar(select(func.count()).select_from(Document).where(Document.user_id == user_id))

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

    def delete(self, document: Document) -> None:
        """Xóa document; chunk bị DB xóa theo (ON DELETE CASCADE)."""
        self._session.execute(delete(Document).where(Document.id == document.id, Document.user_id == document.user_id))
        self._session.commit()

    def commit(self) -> None:
        self._session.commit()

    def rollback(self) -> None:
        self._session.rollback()

    def refresh(self, document: Document) -> None:
        self._session.refresh(document)
