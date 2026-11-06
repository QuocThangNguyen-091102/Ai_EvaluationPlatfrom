"""create benchmark runs; link evaluation runs to a benchmark

Revision ID: 0009
Revises: 0008
Create Date: 2026-11-06
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None

JSONB = postgresql.JSONB(astext_type=sa.Text())


def upgrade() -> None:
    op.create_table(
        "benchmark_runs",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("dataset_version_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("varied_variable", sa.String(length=30), nullable=False),
        sa.Column("status", sa.String(length=20), server_default=sa.text("'pending'"), nullable=False),
        sa.Column("judge_model", sa.String(length=100), nullable=True),
        sa.Column("notes", JSONB, server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("clock_timestamp()"), nullable=False),
        sa.Column("environment", JSONB, server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["dataset_version_id"], ["dataset_versions.id"], deferrable=True, initially="DEFERRED"),
        sa.CheckConstraint("status IN ('pending', 'running', 'completed', 'failed')", name="ck_benchmark_runs_status"),
        sa.CheckConstraint("varied_variable IN ('llm_model', 'top_k', 'prompt_version')", name="ck_benchmark_runs_varied_variable"),
    )
    op.create_index("ix_benchmark_runs_user_id_created_at", "benchmark_runs", ["user_id", "created_at"])

    op.add_column("evaluation_runs", sa.Column("benchmark_run_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_evaluation_runs_benchmark_run_id", "evaluation_runs", "benchmark_runs", ["benchmark_run_id"], ["id"], ondelete="CASCADE"
    )
    op.create_index("ix_evaluation_runs_benchmark_run_id", "evaluation_runs", ["benchmark_run_id"])


def downgrade() -> None:
    op.drop_index("ix_evaluation_runs_benchmark_run_id", table_name="evaluation_runs")
    op.drop_constraint("fk_evaluation_runs_benchmark_run_id", "evaluation_runs", type_="foreignkey")
    op.drop_column("evaluation_runs", "benchmark_run_id")
    op.drop_index("ix_benchmark_runs_user_id_created_at", table_name="benchmark_runs")
    op.drop_table("benchmark_runs")
