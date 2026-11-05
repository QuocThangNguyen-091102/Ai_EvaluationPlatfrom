import os

from pydantic import ValidationError

# Settings yêu cầu DATABASE_URL (từ biến môi trường hoặc file .env ở gốc repo).
# Nếu không có cấu hình nào, dùng URL giả để unit test vẫn import được app.
# Test integration cần DATABASE_URL thật (xem README).
try:
    import app.core.config  # noqa: F401
except ValidationError:
    os.environ["DATABASE_URL"] = "postgresql+psycopg://test:test@127.0.0.1:5432/test"

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app, raise_server_exceptions=False)
