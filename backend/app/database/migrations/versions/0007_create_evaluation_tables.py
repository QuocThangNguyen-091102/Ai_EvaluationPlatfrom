"""create evaluation runs, results and metric results; link retrieved contexts to evaluation results

Revision ID: 0007
Revises: 0006
Create Date: 2026-11-06
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None

DEFERRED = {"deferrable": True, "initially": "DEFERRED"}


def upgrade() -> None:
    op.create_table(
        "evaluation_runs",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("dataset_version_id", sa.Uuid(), nullable=False),
        sa.Column("model_configuration_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=20), server_default=sa.text("'pending'"), nullable=False),
        sa.Column("total_cases", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("completed_cases", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("failed_cases", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("judge_model", sa.String(length=100), nullable=True),
        sa.Column("judge_prompt_version", sa.String(length=50), nullable=True),
        sa.Column("environment", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("categories", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("clock_timestamp()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["dataset_version_id"], ["dataset_versions.id"], **DEFERRED),
        sa.ForeignKeyConstraint(["model_configuration_id"], ["model_configurations.id"], **DEFERRED),
        sa.CheckConstraint("status IN ('pending', 'running', 'completed', 'failed')", name="ck_evaluation_runs_status"),
    )
    op.create_index("ix_evaluation_runs_user_id_created_at", "evaluation_runs", ["user_id", "created_at"])
    op.create_index("ix_evaluation_runs_dataset_version_id", "evaluation_runs", ["dataset_version_id"])

    op.create_table(
        "evaluation_results",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("test_case_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("category", sa.String(length=40), nullable=False),
        sa.Column("answer", sa.Text(), nullable=True),
        sa.Column("insufficient_context", sa.Boolean(), nullable=True),
        sa.Column("mode", sa.String(length=20), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("prompt_tokens", sa.Integer(), nullable=True),
        sa.Column("completion_tokens", sa.Integer(), nullable=True),
        sa.Column("estimated_cost", sa.Numeric(precision=12, scale=6), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("clock_timestamp()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["run_id"], ["evaluation_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["test_case_id"], ["evaluation_test_cases.id"], **DEFERRED),
        sa.UniqueConstraint("run_id", "test_case_id", name="uq_evaluation_results_run_id_test_case_id"),
        sa.CheckConstraint("status IN ('ok', 'error')", name="ck_evaluation_results_status"),
    )

    op.create_table(
        "metric_results",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("evaluation_result_id", sa.Uuid(), nullable=True),
        sa.Column("metric_name", sa.String(length=50), nullable=False),
        sa.Column("k", sa.Integer(), nullable=True),
        sa.Column("value", sa.Float(), nullable=True),
        sa.Column("method", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("clock_timestamp()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["run_id"], ["evaluation_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["evaluation_result_id"], ["evaluation_results.id"], ondelete="CASCADE"),
        sa.CheckConstraint("status IN ('computed', 'failed', 'skipped')", name="ck_metric_results_status"),
        sa.CheckConstraint("method IN ('deterministic', 'llm_judge')", name="ck_metric_results_method"),
        sa.CheckConstraint("(status = 'computed') = (value IS NOT NULL)", name="ck_metric_results_value_only_when_computed"),
    )
    op.create_index("ix_metric_results_run_id_metric_name", "metric_results", ["run_id", "metric_name"])
    op.create_index("ix_metric_results_evaluation_result_id", "metric_results", ["evaluation_result_id"])

    op.add_column("retrieved_contexts", sa.Column("evaluation_result_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_retrieved_contexts_evaluation_result_id", "retrieved_contexts", "evaluation_results",
        ["evaluation_result_id"], ["id"], ondelete="CASCADE",
    )
    op.create_index("ix_retrieved_contexts_evaluation_result_id", "retrieved_contexts", ["evaluation_result_id"])
    op.drop_constraint("ck_retrieved_contexts_one_owner", "retrieved_contexts", type_="check")
    op.create_check_constraint(
        "ck_retrieved_contexts_one_owner", "retrieved_contexts", "num_nonnulls(chat_message_id, evaluation_result_id) = 1"
    )


def downgrade() -> None:
    op.drop_constraint("ck_retrieved_contexts_one_owner", "retrieved_contexts", type_="check")
    op.execute("DELETE FROM retrieved_contexts WHERE chat_message_id IS NULL")
    op.create_check_constraint("ck_retrieved_contexts_one_owner", "retrieved_contexts", "num_nonnulls(chat_message_id) = 1")
    op.drop_index("ix_retrieved_contexts_evaluation_result_id", table_name="retrieved_contexts")
    op.drop_constraint("fk_retrieved_contexts_evaluation_result_id", "retrieved_contexts", type_="foreignkey")
    op.drop_column("retrieved_contexts", "evaluation_result_id")
    op.drop_table("metric_results")
    op.drop_table("evaluation_results")
    op.drop_table("evaluation_runs")
