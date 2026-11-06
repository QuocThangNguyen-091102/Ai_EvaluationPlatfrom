from app.core.exceptions import AppError
from app.core.security import (
    InvalidTokenError,
    create_access_token,
    decode_access_token,
    hash_password,
    spend_password_check_time,
    verify_password,
)
from app.models.user import SANDBOX_EMAIL_DOMAIN, User
from app.repositories.user_repository import DuplicateEmailError, UserRepository

_BEARER_HEADERS = {"WWW-Authenticate": "Bearer"}


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _unauthorized(message: str) -> AppError:
    return AppError(401, "unauthorized", message, headers=_BEARER_HEADERS)


class AuthService:
    """Use case đăng ký, đăng nhập và xác thực token."""

    def __init__(self, users: UserRepository) -> None:
        self._users = users

    def register(self, email: str, password: str) -> User:
        normalized = _normalize_email(email)
        if normalized.endswith("@" + SANDBOX_EMAIL_DOMAIN):
            raise AppError(422, "validation_error", "Tên miền email này dành riêng cho hệ thống")
        if self._users.get_by_email(normalized) is not None:
            raise AppError(409, "conflict", "Email đã được đăng ký")
        try:
            return self._users.create(normalized, hash_password(password))
        except DuplicateEmailError:
            # Hai request đăng ký cùng email chạy song song: request đến sau thua ở ràng buộc duy nhất.
            raise AppError(409, "conflict", "Email đã được đăng ký") from None

    def login(self, email: str, password: str) -> tuple[str, int]:
        user = self._users.get_by_email(_normalize_email(email))
        if user is None:
            spend_password_check_time(password)
            raise _unauthorized("Email hoặc mật khẩu không đúng")
        if not verify_password(password, user.password_hash) or not user.is_active:
            raise _unauthorized("Email hoặc mật khẩu không đúng")
        return create_access_token(user.id)

    def get_user_from_token(self, token: str) -> User:
        try:
            user_id = decode_access_token(token)
        except InvalidTokenError:
            raise _unauthorized("Token không hợp lệ hoặc đã hết hạn") from None
        user = self._users.get_by_id(user_id)
        if user is None or not user.is_active:
            raise _unauthorized("Token không hợp lệ hoặc đã hết hạn")
        return user
