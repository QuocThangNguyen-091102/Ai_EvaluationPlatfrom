"""Băm và kiểm tra mật khẩu, tạo và giải mã JWT.

Không ghi mật khẩu hay token vào log ở bất kỳ đâu trong file này.
"""

import uuid
from datetime import datetime, timedelta, timezone

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from app.core.config import settings

_JWT_ALGORITHM = "HS256"
_hasher = PasswordHasher()
# Băm sẵn một mật khẩu giả để dùng khi email không tồn tại, giúp thời gian phản hồi lúc đăng nhập
# gần giống nhau dù email có tồn tại hay không (giảm khả năng dò email đã đăng ký).
_DUMMY_HASH = _hasher.hash("mật-khẩu-giả-chỉ-để-cân-bằng-thời-gian")


class InvalidTokenError(Exception):
    """Token sai chữ ký, hết hạn, hoặc thiếu thông tin bắt buộc."""


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


def spend_password_check_time(password: str) -> None:
    """Tốn một lần kiểm tra mật khẩu giả; dùng khi không tìm thấy user."""
    verify_password(password, _DUMMY_HASH)


def create_access_token(user_id: uuid.UUID, *, now: datetime | None = None) -> tuple[str, int]:
    """Trả về (token, số giây còn hiệu lực)."""
    issued_at = now or datetime.now(timezone.utc)
    lifetime = timedelta(minutes=settings.jwt_expire_minutes)
    claims = {"sub": str(user_id), "iat": issued_at, "exp": issued_at + lifetime}
    token = jwt.encode(claims, settings.jwt_secret, algorithm=_JWT_ALGORITHM)
    return token, int(lifetime.total_seconds())


def decode_access_token(token: str) -> uuid.UUID:
    """Trả về user_id trong token, hoặc ném InvalidTokenError."""
    try:
        claims = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[_JWT_ALGORITHM],  # chỉ nhận đúng thuật toán, không nhận "none"
            options={"require": ["exp", "iat", "sub"]},
        )
        return uuid.UUID(claims["sub"])
    except (jwt.PyJWTError, ValueError, KeyError) as exc:
        raise InvalidTokenError("Token không hợp lệ") from exc
