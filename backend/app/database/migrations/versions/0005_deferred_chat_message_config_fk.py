"""chat_messages.model_configuration_id: deferred foreign key so deleting a user cascades cleanly

RESTRICT (và cả NO ACTION) kiểm tra trong lúc PostgreSQL đang xóa dây chuyền, trước khi tin nhắn bị xóa, nên chặn
nhầm việc xóa user. Hoãn kiểm tra tới lúc commit thì xóa user chạy được, còn xóa riêng cấu hình đang dùng vẫn bị chặn.

Revision ID: 0005
Revises: 0004
Create Date: 2026-11-06
"""
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None

CONSTRAINT = "chat_messages_model_configuration_id_fkey"


def upgrade() -> None:
    op.drop_constraint(CONSTRAINT, "chat_messages", type_="foreignkey")
    op.create_foreign_key(
        CONSTRAINT, "chat_messages", "model_configurations", ["model_configuration_id"], ["id"],
        deferrable=True, initially="DEFERRED",
    )


def downgrade() -> None:
    op.drop_constraint(CONSTRAINT, "chat_messages", type_="foreignkey")
    op.create_foreign_key(
        CONSTRAINT, "chat_messages", "model_configurations", ["model_configuration_id"], ["id"], ondelete="RESTRICT"
    )
