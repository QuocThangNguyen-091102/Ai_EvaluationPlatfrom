"""create evaluation datasets, versions and test cases

Revision ID: 0006
Revises: 0005
Create Date: 2026-11-06
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "evaluation_datasets",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "name", name="uq_evaluation_datasets_user_id_name"),
    )
    op.create_index("ix_evaluation_datasets_user_id", "evaluation_datasets", ["user_id"])

    op.create_table(
        "dataset_versions",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("dataset_id", sa.Uuid(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), server_default=sa.text("'draft'"), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["dataset_id"], ["evaluation_datasets.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("dataset_id", "version_number", name="uq_dataset_versions_dataset_id_version_number"),
        sa.CheckConstraint("status IN ('draft', 'reviewed')", name="ck_dataset_versions_status"),
        sa.CheckConstraint("version_number >= 1", name="ck_dataset_versions_version_number"),
    )

    op.create_table(
        "evaluation_test_cases",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("dataset_version_id", sa.Uuid(), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("ground_truth_answer", sa.Text(), nullable=True),
        sa.Column("reference_contexts", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("source_note", sa.Text(), nullable=True),
        sa.Column("question_type", sa.String(length=30), nullable=False),
        sa.Column("difficulty", sa.String(length=20), nullable=False),
        sa.Column("expected_behavior", sa.String(length=30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("clock_timestamp()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["dataset_version_id"], ["dataset_versions.id"], ondelete="CASCADE"),
        sa.CheckConstraint("question_type IN ('fact', 'multi_hop', 'summarization', 'unanswerable')", name="ck_evaluation_test_cases_question_type"),
        sa.CheckConstraint("difficulty IN ('easy', 'medium', 'hard')", name="ck_evaluation_test_cases_difficulty"),
        sa.CheckConstraint("expected_behavior IN ('answer', 'insufficient_context')", name="ck_evaluation_test_cases_expected_behavior"),
        sa.CheckConstraint(
            "(expected_behavior = 'answer' AND ground_truth_answer IS NOT NULL) OR "
            "(expected_behavior = 'insufficient_context' AND ground_truth_answer IS NULL)",
            name="ck_evaluation_test_cases_ground_truth",
        ),
    )
    op.create_index("ix_evaluation_test_cases_dataset_version_id", "evaluation_test_cases", ["dataset_version_id"])


def downgrade() -> None:
    op.drop_table("evaluation_test_cases")
    op.drop_table("dataset_versions")
    op.drop_table("evaluation_datasets")
