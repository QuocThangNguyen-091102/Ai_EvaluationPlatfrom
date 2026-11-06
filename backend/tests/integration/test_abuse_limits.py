import pytest

from app.api.routes.auth import login_limiter
from app.core.config import settings
from app.core.exceptions import AppError
from app.core.rate_limit import AttemptLimiter

pytestmark = pytest.mark.integration

PASSWORD = "mat-khau-thu-nghiem-1"


@pytest.fixture(autouse=True)
def isolated_upload_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "upload_dir", str(tmp_path))


def _register(client, email):
    return client.post("/api/v1/auth/register", json={"email": email, "password": PASSWORD})


def _login(client, email, password=PASSWORD):
    return client.post("/api/v1/auth/login", json={"email": email, "password": password})


def test_repeated_wrong_passwords_are_blocked_with_retry_after(api_client):
    _register(api_client, "a@example.com")
    for _ in range(settings.login_max_failures):
        assert _login(api_client, "a@example.com", "sai-mat-khau-123").status_code == 401

    blocked = _login(api_client, "a@example.com")  # đúng mật khẩu cũng bị chặn khi đang khóa

    assert blocked.status_code == 429
    assert int(blocked.headers["Retry-After"]) > 0
    assert blocked.json()["error"]["code"] == "rate_limited"


def test_successful_login_resets_the_failure_count(api_client):
    _register(api_client, "b@example.com")
    for _ in range(settings.login_max_failures - 1):
        _login(api_client, "b@example.com", "sai-mat-khau-123")
    assert _login(api_client, "b@example.com").status_code == 200

    assert _login(api_client, "b@example.com", "sai-mat-khau-123").status_code == 401  # không bị khóa


def test_locking_one_account_does_not_block_another(api_client):
    _register(api_client, "c@example.com")
    _register(api_client, "d@example.com")
    for _ in range(settings.login_max_failures):
        _login(api_client, "c@example.com", "sai-mat-khau-123")

    assert _login(api_client, "d@example.com").status_code == 200


def test_registration_attempts_are_limited_per_ip(api_client):
    for i in range(settings.register_max_attempts):
        _register(api_client, f"user{i}@example.com")

    assert _register(api_client, "one-more@example.com").status_code == 429


def test_registration_can_be_closed(api_client, monkeypatch):
    monkeypatch.setattr(settings, "registration_enabled", False)

    response = _register(api_client, "late@example.com")

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "registration_closed"


def test_document_count_per_user_is_capped(api_client, make_authenticated_user, monkeypatch):
    monkeypatch.setattr(settings, "max_documents_per_user", 1)
    headers = make_authenticated_user()
    first = api_client.post("/api/v1/documents", headers=headers, files={"file": ("a.txt", b"noi dung mot", "text/plain")})
    assert first.status_code == 202

    second = api_client.post("/api/v1/documents", headers=headers, files={"file": ("b.txt", b"noi dung hai", "text/plain")})

    assert second.status_code == 409


def test_window_expires():
    now = [0.0]
    limiter = AttemptLimiter(limit=2, window_seconds=60, clock=lambda: now[0])
    limiter.hit("k")
    limiter.hit("k")
    with pytest.raises(AppError):
        limiter.check("k")

    now[0] = 61
    limiter.check("k")  # hết cửa sổ thì được thử lại


def test_limiter_is_cleared_between_tests():
    assert login_limiter._attempts == {}
