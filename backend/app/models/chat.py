import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Numeric, String, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class ChatSession(Base):
    """Một cuộc hội thoại của một user."""

    __tablename__ = "chat_sessions"
    __table_args__ = (Index("ix_chat_sessions_user_id_created_at", "user_id", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ChatMessage(Base):
    """Một câu hỏi (role user) hoặc câu trả lời (role assistant) trong session."""

    __tablename__ = "chat_messages"
    __table_args__ = (
        CheckConstraint("role IN ('user', 'assistant')", name="ck_chat_messages_role"),
        Index("ix_chat_messages_session_id_created_at", "session_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("chat_sessions.id", ondelete="CASCADE"))
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    # Chỉ có ở message assistant. RESTRICT: không xóa được cấu hình đang có message tham chiếu.
    model_configuration_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("model_configurations.id", ondelete="RESTRICT")
    )
    insufficient_context: Mapped[bool] = mapped_column(server_default=text("false"))
    latency_ms: Mapped[int | None]
    prompt_tokens: Mapped[int | None]
    completion_tokens: Mapped[int | None]
    # Chi phí ước tính (không phải hóa đơn thật); cách ước tính ghi trong báo cáo.
    estimated_cost: Mapped[Decimal | None] = mapped_column(Numeric(12, 6))
    error_message: Mapped[str | None] = mapped_column(Text)
    # clock_timestamp() (giờ lúc ghi từng dòng), không dùng now() (giờ bắt đầu transaction): câu hỏi và câu trả lời
    # ghi trong cùng transaction phải có thứ tự thời gian rõ ràng.
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.clock_timestamp())
