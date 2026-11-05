from app.database.session import get_session
from app.main import app


class _WorkingSession:
    def execute(self, *_args, **_kwargs):
        return None


class _BrokenSession:
    def execute(self, *_args, **_kwargs):
        raise ConnectionError("database down")


def _override_session(session):
    app.dependency_overrides[get_session] = lambda: session


def teardown_function():
    app.dependency_overrides.clear()


def test_health_reports_ok_when_database_responds(client):
    _override_session(_WorkingSession())

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


def test_health_returns_503_when_database_fails(client):
    _override_session(_BrokenSession())

    response = client.get("/health")

    assert response.status_code == 503
    assert response.json() == {"status": "degraded", "database": "error"}
