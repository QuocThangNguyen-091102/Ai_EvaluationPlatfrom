import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base

DOCUMENT_STATUSES = ("uploaded", "processing", "ready", "failed")


class Document(Base):
    """Metadata của một file đã upload và trạng thái xử lý (xem docs/07_database.md)."""

    __tablename__ = "documents"
    __table_args__ = (
        # Mỗi user chỉ có một bản của cùng nội dung (phát hiện upload trùng).
        UniqueConstraint("user_id", "content_hash", name="uq_documents_user_id_content_hash"),
        # Đích tham chiếu của khóa ngoại kép từ document_chunks (ép chunk.user_id khớp document.user_id).
        UniqueConstraint("id", "user_id", name="uq_documents_id_user_id"),
        CheckConstraint(
            "status IN ('uploaded', 'processing', 'ready', 'failed')",
            name="ck_documents_status",
        ),
        Index("ix_documents_user_id_created_at", "user_id", "created_at"),
        Index("ix_documents_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    filename: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(100))
    size_bytes: Mapped[int] = mapped_column(BigInteger)
    # SHA-256 của nội dung, dạng hex (64 ký tự).
    content_hash: Mapped[str] = mapped_column(String(64))
    storage_path: Mapped[str] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(20), server_default=text("'uploaded'"))
    error_message: Mapped[str | None] = mapped_column(Text)
    # Cấu hình đã dùng để xử lý: chunk size, overlap, embedding model.
    processing_config: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
