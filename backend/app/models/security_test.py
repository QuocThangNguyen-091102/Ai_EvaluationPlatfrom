import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base

_DEFERRED = {"deferrable": True, "initially": "DEFERRED"}
SECURITY_CATEGORIES = ("prompt_injection", "jailbreak", "data_leakage", "access_control", "malicious_documents")


class SecurityTestCase(Base):
    """Bản chụp một test case YAML (nguồn chuẩn ở `security/test_cases/`). Dùng chung cho mọi user, không có user_id."""

    __tablename__ = "security_test_cases"
    __table_args__ = (
        UniqueConstraint("case_key", "content_hash", name="uq_security_test_cases_case_key_content_hash"),
        CheckConstraint(
            "category IN ('prompt_injection', 'jailbreak', 'data_leakage', 'access_control', 'malicious_documents')",
            name="ck_security_test_cases_category",
        ),
        CheckConstraint("default_severity IN ('critical', 'high', 'medium', 'low')", name="ck_security_test_cases_severity"),
        Index("ix_security_test_cases_category", "category"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    case_key: Mapped[str] = mapped_column(String(20))
    case_version: Mapped[int]
    content_hash: Mapped[str] = mapped_column(String(64))
    category: Mapped[str] = mapped_column(String(40))
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)
    # Câu hỏi và phạm vi truy xuất, còn nguyên placeholder canary.
    input_payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    setup: Mapped[dict[str, Any]] = mapped_column(JSONB)
    expected_behavior: Mapped[str] = mapped_column(Text)
    evaluation_criteria: Mapped[dict[str, Any]] = mapped_column(JSONB)
    default_severity: Mapped[str] = mapped_column(String(20))
    requires_llm: Mapped[bool]
    mitigation: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SecurityTestRun(Base):
    __tablename__ = "security_test_runs"
    __table_args__ = (
        CheckConstraint("status IN ('pending', 'running', 'completed', 'failed')", name="ck_security_test_runs_status"),
        Index("ix_security_test_runs_user_id_created_at", "user_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    model_configuration_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("model_configurations.id", **_DEFERRED))
    status: Mapped[str] = mapped_column(String(20), server_default=text("'pending'"))
    # Nhóm được chọn; rỗng nghĩa là cả 5 nhóm.
    categories: Mapped[list[str]] = mapped_column(JSONB, server_default=text("'[]'::jsonb"))
    total_cases: Mapped[int] = mapped_column(server_default=text("0"))
    completed_cases: Mapped[int] = mapped_column(server_default=text("0"))
    judge_model: Mapped[str | None] = mapped_column(String(100))
    judge_prompt_version: Mapped[str | None] = mapped_column(String(50))
    summary: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    environment: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    coverage_notes: Mapped[list[str]] = mapped_column(JSONB, server_default=text("'[]'::jsonb"))
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.clock_timestamp())


class SecurityTestResult(Base):
    __tablename__ = "security_test_results"
    __table_args__ = (
        UniqueConstraint("run_id", "test_case_id", name="uq_security_test_results_run_id_test_case_id"),
        CheckConstraint("status IN ('pass', 'fail', 'error', 'skipped')", name="ck_security_test_results_status"),
        CheckConstraint("evaluator IN ('rule', 'judge', 'none')", name="ck_security_test_results_evaluator"),
        Index("ix_security_test_results_run_id_status", "run_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("security_test_runs.id", ondelete="CASCADE"))
    # RESTRICT: không xóa được bản chụp test case khi còn kết quả trỏ tới (test case không thuộc user nên không cần hoãn).
    test_case_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("security_test_cases.id", ondelete="RESTRICT"))
    status: Mapped[str] = mapped_column(String(20))
    severity: Mapped[str] = mapped_column(String(20))
    actual_response: Mapped[str | None] = mapped_column(Text)
    evidence: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    evaluator: Mapped[str] = mapped_column(String(20))
    mitigation: Mapped[str] = mapped_column(Text)
    error_message: Mapped[str | None] = mapped_column(Text)
    latency_ms: Mapped[int | None]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.clock_timestamp())
