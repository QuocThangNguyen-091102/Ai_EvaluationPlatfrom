"""create users, documents and document_chunks

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-05
"""
import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

EMBEDDING_DIMENSIONS = 384


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )

    op.create_table(
        "documents",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("storage_path", sa.String(length=500), nullable=False),
        sa.Column("status", sa.String(length=20), server_default=sa.text("'uploaded'"), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("processing_config", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "content_hash", name="uq_documents_user_id_content_hash"),
        sa.UniqueConstraint("id", "user_id", name="uq_documents_id_user_id"),
        sa.CheckConstraint(
            "status IN ('uploaded', 'processing', 'ready', 'failed')",
            name="ck_documents_status",
        ),
    )
    op.create_index("ix_documents_user_id_created_at", "documents", ["user_id", "created_at"])
    op.create_index("ix_documents_status", "documents", ["status"])

    op.create_table(
        "document_chunks",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("char_start", sa.Integer(), nullable=False),
        sa.Column("char_end", sa.Integer(), nullable=False),
        sa.Column("embedding", Vector(EMBEDDING_DIMENSIONS), nullable=False),
        sa.Column("embedding_model", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["document_id", "user_id"],
            ["documents.id", "documents.user_id"],
            ondelete="CASCADE",
            name="fk_document_chunks_document_id_user_id",
        ),
        sa.UniqueConstraint("document_id", "chunk_index", name="uq_document_chunks_document_id_chunk_index"),
    )
    op.create_index("ix_document_chunks_user_id", "document_chunks", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_document_chunks_user_id", table_name="document_chunks")
    op.drop_table("document_chunks")
    op.drop_index("ix_documents_status", table_name="documents")
    op.drop_index("ix_documents_user_id_created_at", table_name="documents")
    op.drop_table("documents")
    op.drop_table("users")
