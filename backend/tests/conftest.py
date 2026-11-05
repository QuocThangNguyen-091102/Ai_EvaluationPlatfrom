import os
from collections.abc import Iterator
from pathlib import Path

from pydantic import ValidationError

# Settings yêu cầu DATABASE_URL (từ biến môi trường hoặc file .env ở gốc repo).
# Nếu không có cấu hình nào, dùng URL giả để unit test vẫn import được app.
# Test integration cần DATABASE_URL thật (xem README).
try:
    import app.core.config  # noqa: F401
except ValidationError:
    os.environ["DATABASE_URL"] = "postgresql+psycopg://test:test@127.0.0.1:5432/test"

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.database.session import get_engine
from app.main import app

BACKEND_DIR = Path(__file__).resolve().parent.parent


@pytest.fixture
def client() -> TestClient:
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture(scope="session")
def migrated_database() -> None:
    """Đưa DB test lên migration mới nhất. Chỉ test integration dùng fixture này."""
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "app" / "database" / "migrations"))
    command.upgrade(config, "head")


@pytest.fixture
def db_session(migrated_database) -> Iterator[Session]:
    """Một session chạy trong transaction và luôn rollback, nên test không để lại dữ liệu."""
    connection = get_engine().connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()
