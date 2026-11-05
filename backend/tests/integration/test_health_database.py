import pytest

pytestmark = pytest.mark.integration


def test_health_reports_database_ok_with_real_postgres(client):
    """Cần db chạy: `docker compose up -d db`. Không dùng session giả."""
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}
