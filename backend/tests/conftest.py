import os

# Phải đặt trước khi import `app`: Settings yêu cầu DATABASE_URL.
# Giá trị mặc định này trỏ tới db chạy bằng docker compose trên máy host (cổng 127.0.0.1:5432).
# Biến môi trường hoặc file .env của bạn (nếu có) được ưu tiên.
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://app:DEV_PASSWORD_REDACTED@127.0.0.1:5432/ai_eval")

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app, raise_server_exceptions=False)
