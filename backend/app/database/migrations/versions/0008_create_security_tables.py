"""create security test cases, runs and results; link retrieved contexts to security results

Revision ID: 0008
Revises: 0007
Create Date: 2026-11-06
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None

DEFERRED = {"deferrable": True, "initially": "DEFERRED"}
JSONB = postgresql.JSONB(astext_type=sa.Text())


def upgrade() -> None:
    op.create_table(
        "security_test_cases",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("case_key", sa.String(length=20), nullable=False),
        sa.Column("case_version", sa.Integer(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("category", sa.String(length=40), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("input_payload", JSONB, nullable=False),
        sa.Column("setup", JSONB, nullable=False),
        sa.Column("expected_behavior", sa.Text(), nullable=False),
        sa.Column("evaluation_criteria", JSONB, nullable=False),
        sa.Column("default_severity", sa.String(length=20), nullable=False),
        sa.Column("requires_llm", sa.Boolean(), nullable=False),
        sa.Column("mitigation", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("case_key", "content_hash", name="uq_security_test_cases_case_key_content_hash"),
        sa.CheckConstraint(
            "category IN ('prompt_injection', 'jailbreak', 'data_leakage', 'access_control', 'malicious_documents')",
            name="ck_security_test_cases_category",
        ),
        sa.CheckConstraint("default_severity IN ('critical', 'high', 'medium', 'low')", name="ck_security_test_cases_severity"),
    )
    op.create_index("ix_security_test_cases_category", "security_test_cases", ["category"])

    op.create_table(
        "security_test_runs",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("model_configuration_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=20), server_default=sa.text("'pending'"), nullable=False),
        sa.Column("categories", JSONB, server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("total_cases", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("completed_cases", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("judge_model", sa.String(length=100), nullable=True),
        sa.Column("judge_prompt_version", sa.String(length=50), nullable=True),
        sa.Column("summary", JSONB, server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("environment", JSONB, server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("coverage_notes", JSONB, server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("clock_timestamp()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["model_configuration_id"], ["model_configurations.id"], **DEFERRED),
        sa.CheckConstraint("status IN ('pending', 'running', 'completed', 'failed')", name="ck_security_test_runs_status"),
    )
    op.create_index("ix_security_test_runs_user_id_created_at", "security_test_runs", ["user_id", "created_at"])

    op.create_table(
        "security_test_results",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("test_case_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("actual_response", sa.Text(), nullable=True),
        sa.Column("evidence", JSONB, server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("evaluator", sa.String(length=20), nullable=False),
        sa.Column("mitigation", sa.Text(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("clock_timestamp()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["run_id"], ["security_test_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["test_case_id"], ["security_test_cases.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("run_id", "test_case_id", name="uq_security_test_results_run_id_test_case_id"),
        sa.CheckConstraint("status IN ('pass', 'fail', 'error', 'skipped')", name="ck_security_test_results_status"),
        sa.CheckConstraint("evaluator IN ('rule', 'judge', 'none')", name="ck_security_test_results_evaluator"),
    )
    op.create_index("ix_security_test_results_run_id_status", "security_test_results", ["run_id", "status"])

    op.add_column("retrieved_contexts", sa.Column("security_test_result_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_retrieved_contexts_security_test_result_id", "retrieved_contexts", "security_test_results",
        ["security_test_result_id"], ["id"], ondelete="CASCADE",
    )
    op.create_index("ix_retrieved_contexts_security_test_result_id", "retrieved_contexts", ["security_test_result_id"])
    op.drop_constraint("ck_retrieved_contexts_one_owner", "retrieved_contexts", type_="check")
    op.create_check_constraint(
        "ck_retrieved_contexts_one_owner",
        "retrieved_contexts",
        "num_nonnulls(chat_message_id, evaluation_result_id, security_test_result_id) = 1",
    )


def downgrade() -> None:
    op.drop_constraint("ck_retrieved_contexts_one_owner", "retrieved_contexts", type_="check")
    op.execute("DELETE FROM retrieved_contexts WHERE security_test_result_id IS NOT NULL")
    op.create_check_constraint(
        "ck_retrieved_contexts_one_owner", "retrieved_contexts", "num_nonnulls(chat_message_id, evaluation_result_id) = 1"
    )
    op.drop_index("ix_retrieved_contexts_security_test_result_id", table_name="retrieved_contexts")
    op.drop_constraint("fk_retrieved_contexts_security_test_result_id", "retrieved_contexts", type_="foreignkey")
    op.drop_column("retrieved_contexts", "security_test_result_id")
    op.drop_index("ix_security_test_results_run_id_status", table_name="security_test_results")
    op.drop_table("security_test_results")
    op.drop_index("ix_security_test_runs_user_id_created_at", table_name="security_test_runs")
    op.drop_table("security_test_runs")
    op.drop_index("ix_security_test_cases_category", table_name="security_test_cases")
    op.drop_table("security_test_cases")
