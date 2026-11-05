import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, UniqueConstraint, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class ModelConfiguration(Base):
    """Một cấu hình RAG đặt tên, dùng cho chat, evaluation, security và benchmark (xem docs/07_database.md).

    Bất biến: muốn đổi thì tạo bản ghi mới, để kết quả cũ luôn truy ngược được cấu hình đã dùng.
    """

    __tablename__ = "model_configurations"
    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_model_configurations_user_id_name"),
        CheckConstraint("top_k >= 1", name="ck_model_configurations_top_k"),
        CheckConstraint("temperature >= 0 AND temperature <= 2", name="ck_model_configurations_temperature"),
        CheckConstraint("chunk_size >= 1", name="ck_model_configurations_chunk_size"),
        CheckConstraint("chunk_overlap >= 0 AND chunk_overlap < chunk_size", name="ck_model_configurations_chunk_overlap"),
        Index("ix_model_configurations_user_id", "user_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(100))
    llm_provider: Mapped[str] = mapped_column(String(50))
    llm_model: Mapped[str] = mapped_column(String(100))
    embedding_provider: Mapped[str] = mapped_column(String(50))
    embedding_model: Mapped[str] = mapped_column(String(100))
    prompt_version: Mapped[str] = mapped_column(String(50))
    top_k: Mapped[int]
    temperature: Mapped[float]
    # Mô tả trạng thái corpus khi chạy (chunk size và overlap tính bằng từ).
    chunk_size: Mapped[int]
    chunk_overlap: Mapped[int]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
