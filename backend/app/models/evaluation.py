import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Numeric, String, Text, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base

# Khóa ngoại "chặn xóa" trỏ tới dữ liệu cũng bị xóa theo user phải hoãn kiểm tra tới lúc commit (quy tắc rút ra ở
# M4-T07): vẫn chặn xóa riêng một dataset version hay cấu hình đang được dùng, nhưng không chặn việc xóa user.
_DEFERRED = {"deferrable": True, "initially": "DEFERRED"}


class EvaluationRun(Base):
    __tablename__ = "evaluation_runs"
    __table_args__ = (
        CheckConstraint("status IN ('pending', 'running', 'completed', 'failed')", name="ck_evaluation_runs_status"),
        Index("ix_evaluation_runs_user_id_created_at", "user_id", "created_at"),
        Index("ix_evaluation_runs_dataset_version_id", "dataset_version_id"),
        Index("ix_evaluation_runs_benchmark_run_id", "benchmark_run_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    dataset_version_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("dataset_versions.id", **_DEFERRED))
    model_configuration_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("model_configurations.id", **_DEFERRED))
    # Thuộc một benchmark (xóa benchmark thì xóa các lượt con); NULL là lượt đánh giá đơn lẻ.
    benchmark_run_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("benchmark_runs.id", ondelete="CASCADE", name="fk_evaluation_runs_benchmark_run_id")
    )
    status: Mapped[str] = mapped_column(String(20), server_default=text("'pending'"))
    total_cases: Mapped[int] = mapped_column(server_default=text("0"))
    completed_cases: Mapped[int] = mapped_column(server_default=text("0"))
    failed_cases: Mapped[int] = mapped_column(server_default=text("0"))
    judge_model: Mapped[str | None] = mapped_column(String(100))
    judge_prompt_version: Mapped[str | None] = mapped_column(String(50))
    # Ảnh chụp mọi thứ cần để tái lập: cấu hình, phiên bản thư viện, cấu hình xử lý của corpus, dataset version.
    environment: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    categories: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.clock_timestamp())


class EvaluationResult(Base):
    __tablename__ = "evaluation_results"
    __table_args__ = (
        UniqueConstraint("run_id", "test_case_id", name="uq_evaluation_results_run_id_test_case_id"),
        CheckConstraint("status IN ('ok', 'error')", name="ck_evaluation_results_status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("evaluation_runs.id", ondelete="CASCADE"))
    test_case_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("evaluation_test_cases.id", **_DEFERRED))
    status: Mapped[str] = mapped_column(String(20))
    category: Mapped[str] = mapped_column(String(40))
    answer: Mapped[str | None] = mapped_column(Text)
    insufficient_context: Mapped[bool | None]
    mode: Mapped[str | None] = mapped_column(String(20))
    error_message: Mapped[str | None] = mapped_column(Text)
    latency_ms: Mapped[int | None]
    prompt_tokens: Mapped[int | None]
    completion_tokens: Mapped[int | None]
    estimated_cost: Mapped[Decimal | None] = mapped_column(Numeric(12, 6))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.clock_timestamp())


class MetricResult(Base):
    """Điểm của một metric, ở mức từng câu (evaluation_result_id có giá trị) hoặc tổng hợp cả lượt (NULL)."""

    __tablename__ = "metric_results"
    __table_args__ = (
        CheckConstraint("status IN ('computed', 'failed', 'skipped')", name="ck_metric_results_status"),
        CheckConstraint("method IN ('deterministic', 'llm_judge')", name="ck_metric_results_method"),
        # Không có số khi không tính được: chỉ trạng thái computed mới được có value.
        CheckConstraint("(status = 'computed') = (value IS NOT NULL)", name="ck_metric_results_value_only_when_computed"),
        Index("ix_metric_results_run_id_metric_name", "run_id", "metric_name"),
        Index("ix_metric_results_evaluation_result_id", "evaluation_result_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("evaluation_runs.id", ondelete="CASCADE"))
    evaluation_result_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("evaluation_results.id", ondelete="CASCADE"))
    metric_name: Mapped[str] = mapped_column(String(50))
    k: Mapped[int | None]
    value: Mapped[float | None]
    method: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20))
    details: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.clock_timestamp())
