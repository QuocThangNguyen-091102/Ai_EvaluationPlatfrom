"""rename prompt identifiers to descriptive names (rag-grounded-citations, judge-strict-json)

Mã prompt đánh số (rag-v1, judge-v1) được đổi thành tên mô tả đặc điểm của prompt. Đổi cả giá trị đã lưu trong cột và
trong bản chụp môi trường (JSONB), để kết quả cũ vẫn khớp với mã prompt hiện có trong code.

Revision ID: 0010
Revises: 0009
Create Date: 2026-11-06
"""
from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None

RENAMES = (("rag-v1", "rag-grounded-citations"), ("judge-v1", "judge-strict-json"))


def _apply(pairs) -> None:
    for old, new in pairs:
        params = {"old": old, "new": new}
        op.execute(_sql("UPDATE model_configurations SET prompt_version = :new WHERE prompt_version = :old", params))
        for table in ("evaluation_runs", "security_test_runs"):
            op.execute(_sql(f"UPDATE {table} SET judge_prompt_version = :new WHERE judge_prompt_version = :old", params))
            op.execute(
                _sql(
                    f"UPDATE {table} SET environment = jsonb_set(environment, '{{model_configuration,prompt_version}}', to_jsonb(CAST(:new AS text))) "
                    "WHERE environment #>> '{model_configuration,prompt_version}' = :old",
                    params,
                )
            )
        op.execute(
            _sql(
                "UPDATE evaluation_runs SET environment = jsonb_set(environment, '{judge,prompt_version}', to_jsonb(CAST(:new AS text))) "
                "WHERE environment #>> '{judge,prompt_version}' = :old",
                params,
            )
        )


def _sql(statement: str, params: dict):
    import sqlalchemy as sa

    return sa.text(statement).bindparams(**params)


def upgrade() -> None:
    _apply(RENAMES)


def downgrade() -> None:
    _apply(tuple((new, old) for old, new in RENAMES))
