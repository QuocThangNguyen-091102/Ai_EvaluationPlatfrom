import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base

QUESTION_TYPES = ("fact", "multi_hop", "summarization", "unanswerable")
DIFFICULTIES = ("easy", "medium", "hard")
EXPECTED_BEHAVIORS = ("answer", "insufficient_context")


class EvaluationDataset(Base):
    __tablename__ = "evaluation_datasets"
    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_evaluation_datasets_user_id_name"),
        Index("ix_evaluation_datasets_user_id", "user_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(150))
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DatasetVersion(Base):
    """Phiên bản của dataset. Đã duyệt (reviewed) thì bất biến: muốn sửa phải tạo phiên bản mới."""

    __tablename__ = "dataset_versions"
    __table_args__ = (
        UniqueConstraint("dataset_id", "version_number", name="uq_dataset_versions_dataset_id_version_number"),
        CheckConstraint("status IN ('draft', 'reviewed')", name="ck_dataset_versions_status"),
        CheckConstraint("version_number >= 1", name="ck_dataset_versions_version_number"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    dataset_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("evaluation_datasets.id", ondelete="CASCADE"))
    version_number: Mapped[int]
    status: Mapped[str] = mapped_column(String(20), server_default=text("'draft'"))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EvaluationTestCase(Base):
    """Một câu hỏi đánh giá.

    reference_contexts: danh sách đoạn chứa đáp án, mỗi phần tử
    {document_content_hash, filename, char_start, char_end, text}. Vị trí tính trên văn bản đã làm sạch của tài liệu,
    không phụ thuộc cách chia chunk, nên đổi chunk size vẫn chấm được.
    """

    __tablename__ = "evaluation_test_cases"
    __table_args__ = (
        CheckConstraint(f"question_type IN {QUESTION_TYPES}", name="ck_evaluation_test_cases_question_type"),
        CheckConstraint(f"difficulty IN {DIFFICULTIES}", name="ck_evaluation_test_cases_difficulty"),
        CheckConstraint(f"expected_behavior IN {EXPECTED_BEHAVIORS}", name="ck_evaluation_test_cases_expected_behavior"),
        # Câu cần trả lời phải có đáp án chuẩn; câu "không đủ thông tin" thì không có.
        CheckConstraint(
            "(expected_behavior = 'answer' AND ground_truth_answer IS NOT NULL) OR "
            "(expected_behavior = 'insufficient_context' AND ground_truth_answer IS NULL)",
            name="ck_evaluation_test_cases_ground_truth",
        ),
        Index("ix_evaluation_test_cases_dataset_version_id", "dataset_version_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    dataset_version_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("dataset_versions.id", ondelete="CASCADE"))
    question: Mapped[str] = mapped_column(Text)
    ground_truth_answer: Mapped[str | None] = mapped_column(Text)
    reference_contexts: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, server_default=text("'[]'::jsonb"))
    source_note: Mapped[str | None] = mapped_column(Text)
    question_type: Mapped[str] = mapped_column(String(30))
    difficulty: Mapped[str] = mapped_column(String(20))
    expected_behavior: Mapped[str] = mapped_column(String(30))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.clock_timestamp())
