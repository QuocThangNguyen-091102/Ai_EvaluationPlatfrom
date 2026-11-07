import uuid
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from pydantic import ValidationError

from app.core.config import Settings, settings
from app.core.security import (
    InvalidTokenError,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


@pytest.mark.parametrize("secret", ["change-me-to-a-long-random-string", "CHANGE-ME-padding-padding-padding-123"])
def test_settings_reject_placeholder_jwt_secret(secret):
    with pytest.raises(ValidationError, match="chuỗi mẫu"):
        Settings(database_url="postgresql+psycopg://u:p@localhost/db", jwt_secret=secret)


def test_settings_accept_random_jwt_secret():
    loaded = Settings(database_url="postgresql+psycopg://u:p@localhost/db", jwt_secret="x" * 16 + "f3Kq9-Zr81mPw0aLt")

    assert loaded.jwt_secret.startswith("x")


def test_password_is_hashed_not_stored_as_plain_text():
    hashed = hash_password("mật khẩu của tôi")

    assert hashed != "mật khẩu của tôi"
    assert "mật khẩu của tôi" not in hashed


def test_same_password_gets_different_hashes_because_of_salt():
    assert hash_password("same-password") != hash_password("same-password")


def test_verify_password_accepts_correct_and_rejects_wrong_password():
    hashed = hash_password("correct-password")

    assert verify_password("correct-password", hashed) is True
    assert verify_password("wrong-password", hashed) is False


def test_verify_password_returns_false_for_a_corrupt_hash_instead_of_raising():
    assert verify_password("anything", "not-a-valid-hash") is False


def test_token_round_trip_returns_the_same_user_id():
    user_id = uuid.uuid4()

    token, expires_in = create_access_token(user_id)

    assert decode_access_token(token) == user_id
    assert expires_in == settings.jwt_expire_minutes * 60


def test_expired_token_is_rejected():
    long_ago = datetime.now(timezone.utc) - timedelta(minutes=settings.jwt_expire_minutes + 5)
    token, _ = create_access_token(uuid.uuid4(), now=long_ago)

    with pytest.raises(InvalidTokenError):
        decode_access_token(token)


def test_token_signed_with_another_secret_is_rejected():
    forged = jwt.encode(
        {"sub": str(uuid.uuid4()), "iat": datetime.now(timezone.utc), "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
        "một-khóa-khác-dài-ít-nhất-32-ký-tự-0123456789",
        algorithm="HS256",
    )

    with pytest.raises(InvalidTokenError):
        decode_access_token(forged)


def test_unsigned_token_with_alg_none_is_rejected():
    unsigned = jwt.encode(
        {"sub": str(uuid.uuid4()), "iat": datetime.now(timezone.utc), "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
        key=None,
        algorithm="none",
    )

    with pytest.raises(InvalidTokenError):
        decode_access_token(unsigned)


def test_token_without_required_claims_is_rejected():
    no_sub = jwt.encode({"exp": datetime.now(timezone.utc) + timedelta(hours=1)}, settings.jwt_secret, algorithm="HS256")

    with pytest.raises(InvalidTokenError):
        decode_access_token(no_sub)


def test_token_with_non_uuid_subject_is_rejected():
    bad_sub = jwt.encode(
        {"sub": "không-phải-uuid", "iat": datetime.now(timezone.utc), "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
        settings.jwt_secret,
        algorithm="HS256",
    )

    with pytest.raises(InvalidTokenError):
        decode_access_token(bad_sub)


def test_garbage_string_is_rejected():
    with pytest.raises(InvalidTokenError):
        decode_access_token("đây-không-phải-jwt")
