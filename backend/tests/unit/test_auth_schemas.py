import pytest
from pydantic import ValidationError

from app.core.config import settings
from app.schemas.auth import RegisterRequest


def test_register_accepts_valid_email_and_password():
    payload = RegisterRequest(email="user@example.com", password="x" * settings.password_min_length)

    assert payload.email == "user@example.com"


def test_register_rejects_password_shorter_than_the_configured_minimum():
    with pytest.raises(ValidationError):
        RegisterRequest(email="user@example.com", password="x" * (settings.password_min_length - 1))


def test_register_rejects_extremely_long_password():
    with pytest.raises(ValidationError):
        RegisterRequest(email="user@example.com", password="x" * 1000)


@pytest.mark.parametrize("bad_email", ["không-phải-email", "thiếu@", "@thiếu.com", ""])
def test_register_rejects_malformed_email(bad_email):
    with pytest.raises(ValidationError):
        RegisterRequest(email=bad_email, password="a-valid-password")
