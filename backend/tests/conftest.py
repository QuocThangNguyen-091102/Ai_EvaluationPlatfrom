import os
from collections.abc import Iterator
from contextlib import nullcontext
from pathlib import Path

from pydantic import ValidationError

# Settings yêu cầu DATABASE_URL và JWT_SECRET (từ biến môi trường hoặc file .env ở gốc repo).
# Nếu thiếu, dùng giá trị giả để unit test vẫn import được app; giá trị thật (nếu có) luôn được ưu tiên.
# Test integration cần DATABASE_URL thật (xem README).
try:
    import app.core.config  # noqa: F401
except ValidationError:
    os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://test:test@127.0.0.1:5432/test")
    os.environ.setdefault("JWT_SECRET", "chi-dung-cho-test-khong-phai-secret-that-0123456789")

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from ai_engine.generation.cost_estimator import PriceTable
from ai_engine.pipeline.rag_pipeline import RagPipeline
from app.api.dependencies import (
    get_benchmark_run_service,
    get_evaluation_run_service,
    get_ingestion_service,
    get_pipeline,
    get_security_run_service,
)
from app.core.rag_defaults import get_rag_defaults
from app.database.session import get_engine, get_session
from app.main import app
from app.services.evaluation_service import EvaluationRunService
from app.services.benchmark_service import BenchmarkRunService
from app.services.ingestion_service import IngestionService
from app.services.security_service import SecurityRunService
from tests.fakes import HashEmbedder, ScriptedLlm

BACKEND_DIR = Path(__file__).resolve().parent.parent


@pytest.fixture
def client() -> TestClient:
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def test_embedder() -> HashEmbedder:
    return HashEmbedder()


@pytest.fixture
def ingestion_service(db_session, test_embedder) -> IngestionService:
    """Xử lý nền dùng chung session của test và embedder giả (không tải model thật)."""
    return IngestionService(
        session_factory=lambda: nullcontext(db_session),
        embedder_provider=lambda: test_embedder,
        defaults=get_rag_defaults(),
    )


@pytest.fixture
def scripted_llm() -> ScriptedLlm:
    return ScriptedLlm()


@pytest.fixture
def rag_pipeline(test_embedder, scripted_llm) -> RagPipeline:
    """Pipeline thật (cùng code với sản phẩm) nhưng dùng embedder giả và LLM giả."""
    return RagPipeline(embedder=test_embedder, llm_for=lambda config: scripted_llm, price_table=PriceTable([]))


@pytest.fixture
def judge_llm() -> ScriptedLlm:
    """LLM giả đóng vai judge; test đặt `_respond` để điều khiển phản hồi."""
    return ScriptedLlm(lambda messages: '{"claims": [{"claim": "x", "supported": true}]}' if "NGỮ CẢNH" in messages[1].content else '{"score": 5, "reason": "ok"}')


@pytest.fixture
def evaluation_run_service(db_session, rag_pipeline, judge_llm) -> EvaluationRunService:
    return EvaluationRunService(
        session_factory=lambda: nullcontext(db_session),
        pipeline_provider=lambda: rag_pipeline,
        judge_client_for=lambda model: judge_llm,
    )


TEST_SECRETS = {"JWT_SECRET": "test-secret-value-xyz"}


@pytest.fixture
def security_run_service(db_session, rag_pipeline, test_embedder, judge_llm) -> SecurityRunService:
    return SecurityRunService(
        session_factory=lambda: nullcontext(db_session),
        pipeline_provider=lambda: rag_pipeline,
        embedder_provider=lambda: test_embedder,
        judge_client_for=lambda model: judge_llm,
        secrets_provider=lambda: TEST_SECRETS,
    )


@pytest.fixture
def api_client(db_session, ingestion_service, rag_pipeline, evaluation_run_service, security_run_service) -> Iterator[TestClient]:
    """Client gọi API thật nhưng mọi truy cập DB đi qua db_session (rollback cuối test, không để lại dữ liệu)."""
    overrides = {
        get_session: lambda: db_session,
        get_ingestion_service: lambda: ingestion_service,
        get_pipeline: lambda: rag_pipeline,
        get_evaluation_run_service: lambda: evaluation_run_service,
        get_security_run_service: lambda: security_run_service,
        get_benchmark_run_service: lambda: BenchmarkRunService(
            session_factory=lambda: nullcontext(db_session), evaluation_runner=evaluation_run_service
        ),
    }
    app.dependency_overrides.update(overrides)
    try:
        yield TestClient(app, raise_server_exceptions=False)
    finally:
        for dependency in overrides:
            app.dependency_overrides.pop(dependency, None)


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


@pytest.fixture
def make_authenticated_user(api_client):
    """Tạo user mới qua API và trả về header Authorization để gọi các endpoint cần đăng nhập."""
    import uuid

    def _make() -> dict[str, str]:
        email = f"{uuid.uuid4().hex[:12]}@example.com"
        password = "a-strong-password"
        api_client.post("/api/v1/auth/register", json={"email": email, "password": password})
        token = api_client.post("/api/v1/auth/login", json={"email": email, "password": password}).json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    return _make
