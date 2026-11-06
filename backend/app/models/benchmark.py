import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base

_DEFERRED = {"deferrable": True, "initially": "DEFERRED"}


class BenchmarkRun(Base):
    """Nhóm các lượt đánh giá trên cùng dataset version, mỗi lượt một cấu hình, chỉ khác nhau ở một biến."""

    __tablename__ = "benchmark_runs"
    __table_args__ = (
        CheckConstraint("status IN ('pending', 'running', 'completed', 'failed')", name="ck_benchmark_runs_status"),
        CheckConstraint("varied_variable IN ('llm_model', 'top_k', 'prompt_version')", name="ck_benchmark_runs_varied_variable"),
        Index("ix_benchmark_runs_user_id_created_at", "user_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    dataset_version_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("dataset_versions.id", **_DEFERRED))
    name: Mapped[str] = mapped_column(String(100))
    varied_variable: Mapped[str] = mapped_column(String(30))
    status: Mapped[str] = mapped_column(String(20), server_default=text("'pending'"))
    judge_model: Mapped[str | None] = mapped_column(String(100))
    # Cảnh báo về điều kiện so sánh (ví dụ cấu hình khác nhau ở nhiều biến).
    notes: Mapped[list[str]] = mapped_column(JSONB, server_default=text("'[]'::jsonb"))
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.clock_timestamp())
    environment: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
