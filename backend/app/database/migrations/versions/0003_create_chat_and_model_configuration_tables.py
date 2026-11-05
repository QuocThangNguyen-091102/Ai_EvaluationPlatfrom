"""create chat, retrieved context and model configuration tables

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-06
"""
import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "model_configurations",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("llm_provider", sa.String(length=50), nullable=False),
        sa.Column("llm_model", sa.String(length=100), nullable=False),
        sa.Column("embedding_provider", sa.String(length=50), nullable=False),
        sa.Column("embedding_model", sa.String(length=100), nullable=False),
        sa.Column("prompt_version", sa.String(length=50), nullable=False),
        sa.Column("top_k", sa.Integer(), nullable=False),
        sa.Column("temperature", sa.Float(), nullable=False),
        sa.Column("chunk_size", sa.Integer(), nullable=False),
        sa.Column("chunk_overlap", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "name", name="uq_model_configurations_user_id_name"),
        sa.CheckConstraint("top_k >= 1", name="ck_model_configurations_top_k"),
        sa.CheckConstraint("temperature >= 0 AND temperature <= 2", name="ck_model_configurations_temperature"),
        sa.CheckConstraint("chunk_size >= 1", name="ck_model_configurations_chunk_size"),
        sa.CheckConstraint("chunk_overlap >= 0 AND chunk_overlap < chunk_size", name="ck_model_configurations_chunk_overlap"),
    )
    op.create_index("ix_model_configurations_user_id", "model_configurations", ["user_id"])

    op.create_table(
        "chat_sessions",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_chat_sessions_user_id_created_at", "chat_sessions", ["user_id", "created_at"])

    op.create_table(
        "chat_messages",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("model_configuration_id", sa.Uuid(), nullable=True),
        sa.Column("insufficient_context", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("prompt_tokens", sa.Integer(), nullable=True),
        sa.Column("completion_tokens", sa.Integer(), nullable=True),
        sa.Column("estimated_cost", sa.Numeric(precision=12, scale=6), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["session_id"], ["chat_sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["model_configuration_id"], ["model_configurations.id"], ondelete="RESTRICT"),
        sa.CheckConstraint("role IN ('user', 'assistant')", name="ck_chat_messages_role"),
    )
    op.create_index("ix_chat_messages_session_id_created_at", "chat_messages", ["session_id", "created_at"])

    op.create_table(
        "retrieved_contexts",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("chat_message_id", sa.Uuid(), nullable=True),
        sa.Column("chunk_id", sa.Uuid(), nullable=True),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("content_snapshot", sa.Text(), nullable=False),
        sa.Column("document_filename_snapshot", sa.String(length=255), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["chat_message_id"], ["chat_messages.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["chunk_id"], ["document_chunks.id"], ondelete="SET NULL"),
        sa.CheckConstraint("num_nonnulls(chat_message_id) = 1", name="ck_retrieved_contexts_one_owner"),
    )
    op.create_index("ix_retrieved_contexts_chat_message_id", "retrieved_contexts", ["chat_message_id"])
    op.create_index("ix_retrieved_contexts_chunk_id", "retrieved_contexts", ["chunk_id"])


def downgrade() -> None:
    op.drop_table("retrieved_contexts")
    op.drop_table("chat_messages")
    op.drop_table("chat_sessions")
    op.drop_table("model_configurations")
