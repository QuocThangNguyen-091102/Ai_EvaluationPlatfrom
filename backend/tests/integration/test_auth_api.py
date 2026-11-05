import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.core.config import settings
from app.core.security import create_access_token
from app.models import User

pytestmark = pytest.mark.integration

PASSWORD = "a-strong-password"
REGISTER = "/api/v1/auth/register"
LOGIN = "/api/v1/auth/login"
ME = "/api/v1/auth/me"


def _email() -> str:
    return f"{uuid.uuid4().hex[:12]}@example.com"


def _register(client, email=None, password=PASSWORD):
    return client.post(REGISTER, json={"email": email or _email(), "password": password})


def _login_token(client, email, password=PASSWORD) -> str:
    response = client.post(LOGIN, json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def test_register_creates_user_and_never_returns_the_password_hash(api_client):
    email = _email()

    response = _register(api_client, email)

    assert response.status_code == 201
    body = response.json()
    assert set(body) == {"id", "email", "created_at"}
    assert body["email"] == email


def test_password_is_stored_hashed(api_client, db_session):
    email = _email()
    _register(api_client, email)

    stored = db_session.scalar(select(User).where(User.email == email))

    assert stored.password_hash != PASSWORD
    assert PASSWORD not in stored.password_hash


def test_register_rejects_duplicate_email_ignoring_case_and_spaces(api_client):
    email = _email()
    _register(api_client, email)

    response = _register(api_client, f"  {email.upper()}  ")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "conflict"


def test_register_rejects_short_password_with_validation_error(api_client):
    response = _register(api_client, password="short")

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "validation_error"
    assert [item["field"] for item in body["error"]["details"]] == ["password"]


def test_register_rejects_malformed_email(api_client):
    response = _register(api_client, email="không-phải-email")

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_login_returns_a_bearer_token_that_opens_me(api_client):
    email = _email()
    _register(api_client, email)

    login = api_client.post(LOGIN, json={"email": email, "password": PASSWORD})

    assert login.status_code == 200
    body = login.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == settings.jwt_expire_minutes * 60
    me = api_client.get(ME, headers={"Authorization": f"Bearer {body['access_token']}"})
    assert me.status_code == 200
    assert me.json()["email"] == email


def test_login_accepts_email_in_different_case(api_client):
    email = _email()
    _register(api_client, email)

    response = api_client.post(LOGIN, json={"email": email.upper(), "password": PASSWORD})

    assert response.status_code == 200


def test_login_gives_the_same_error_for_wrong_password_and_unknown_email(api_client):
    email = _email()
    _register(api_client, email)

    wrong_password = api_client.post(LOGIN, json={"email": email, "password": "wrong-password"})
    unknown_email = api_client.post(LOGIN, json={"email": _email(), "password": PASSWORD})

    assert wrong_password.status_code == unknown_email.status_code == 401
    assert wrong_password.json() == unknown_email.json()
    assert wrong_password.headers["www-authenticate"] == "Bearer"


def test_login_rejects_inactive_user(api_client, db_session):
    email = _email()
    _register(api_client, email)
    db_session.scalar(select(User).where(User.email == email)).is_active = False
    db_session.flush()

    response = api_client.post(LOGIN, json={"email": email, "password": PASSWORD})

    assert response.status_code == 401


def test_me_without_token_is_unauthorized(api_client):
    response = api_client.get(ME)

    assert response.status_code == 401
    body = response.json()
    assert body["error"]["code"] == "unauthorized"
    assert response.headers["www-authenticate"] == "Bearer"


def test_me_with_malformed_token_is_unauthorized(api_client):
    response = api_client.get(ME, headers={"Authorization": "Bearer not-a-valid-jwt"})

    assert response.status_code == 401


def test_me_with_expired_token_is_unauthorized(api_client):
    email = _email()
    user_id = _register(api_client, email).json()["id"]
    long_ago = datetime.now(timezone.utc) - timedelta(minutes=settings.jwt_expire_minutes + 5)
    expired, _ = create_access_token(uuid.UUID(user_id), now=long_ago)

    response = api_client.get(ME, headers={"Authorization": f"Bearer {expired}"})

    assert response.status_code == 401


def test_me_with_token_of_a_deleted_user_is_unauthorized(api_client, db_session):
    email = _email()
    user_id = _register(api_client, email).json()["id"]
    token = _login_token(api_client, email)
    db_session.delete(db_session.get(User, uuid.UUID(user_id)))
    db_session.flush()

    response = api_client.get(ME, headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401


def test_me_with_token_of_an_inactive_user_is_unauthorized(api_client, db_session):
    email = _email()
    _register(api_client, email)
    token = _login_token(api_client, email)
    db_session.scalar(select(User).where(User.email == email)).is_active = False
    db_session.flush()

    response = api_client.get(ME, headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401


def test_wrong_scheme_in_authorization_header_is_unauthorized(api_client):
    email = _email()
    _register(api_client, email)
    token = _login_token(api_client, email)

    response = api_client.get(ME, headers={"Authorization": f"Basic {token}"})

    assert response.status_code == 401
