import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class RetrievedContext(Base):
    """Chunk đã được truy xuất cho một lần chạy pipeline, kèm điểm (xem docs/07_database.md).

    Lưu bản chụp nội dung chunk để kết quả cũ vẫn đọc được khi tài liệu bị xóa hoặc chunk lại.
    Gắn với đúng một chủ: message chat, kết quả đánh giá hoặc kết quả kiểm thử bảo mật.
    """

    __tablename__ = "retrieved_contexts"
    __table_args__ = (
        CheckConstraint(
            "num_nonnulls(chat_message_id, evaluation_result_id, security_test_result_id) = 1",
            name="ck_retrieved_contexts_one_owner",
        ),
        Index("ix_retrieved_contexts_chat_message_id", "chat_message_id"),
        Index("ix_retrieved_contexts_evaluation_result_id", "evaluation_result_id"),
        Index("ix_retrieved_contexts_security_test_result_id", "security_test_result_id"),
        Index("ix_retrieved_contexts_chunk_id", "chunk_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    chat_message_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("chat_messages.id", ondelete="CASCADE"))
    evaluation_result_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("evaluation_results.id", ondelete="CASCADE", name="fk_retrieved_contexts_evaluation_result_id")
    )
    security_test_result_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("security_test_results.id", ondelete="CASCADE", name="fk_retrieved_contexts_security_test_result_id")
    )
    # SET NULL: xóa tài liệu thì chunk mất nhưng bản ghi này và bản chụp nội dung vẫn còn.
    chunk_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("document_chunks.id", ondelete="SET NULL"))
    rank: Mapped[int]
    score: Mapped[float]
    content_snapshot: Mapped[str] = mapped_column(Text)
    document_filename_snapshot: Mapped[str] = mapped_column(String(255))
    page_number: Mapped[int | None]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
