from fastapi import APIRouter, Depends, Request, status

from app.api.dependencies import get_auth_service, get_current_user
from app.core.config import settings
from app.core.exceptions import AppError
from app.core.rate_limit import AttemptLimiter
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])

login_limiter = AttemptLimiter(limit=settings.login_max_failures, window_seconds=settings.rate_limit_window_seconds)
login_ip_limiter = AttemptLimiter(limit=settings.login_max_failures * 5, window_seconds=settings.rate_limit_window_seconds)
register_limiter = AttemptLimiter(limit=settings.register_max_attempts, window_seconds=settings.rate_limit_window_seconds)


def _client_ip(request: Request) -> str:
    # Sau reverse proxy, uvicorn chạy với --proxy-headers nên request.client là IP thật của người dùng.
    return request.client.host if request.client else "unknown"


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, request: Request, service: AuthService = Depends(get_auth_service)) -> User:
    if not settings.registration_enabled:
        raise AppError(403, "registration_closed", "Máy chủ này đã đóng đăng ký tài khoản mới")
    key = f"register:{_client_ip(request)}"
    register_limiter.check(key)
    register_limiter.hit(key)
    return service.register(payload.email, payload.password)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, request: Request, service: AuthService = Depends(get_auth_service)) -> TokenResponse:
    ip = _client_ip(request)
    account_key, ip_key = f"login:{ip}:{payload.email.strip().lower()}", f"login-ip:{ip}"
    # Chỉ đếm lần sai: người dùng thật đăng nhập đúng không bị ảnh hưởng.
    login_limiter.check(account_key)
    login_ip_limiter.check(ip_key)
    try:
        access_token, expires_in = service.login(payload.email, payload.password)
    except AppError as error:
        if error.status_code == 401:
            login_limiter.hit(account_key)
            login_ip_limiter.hit(ip_key)
        raise
    login_limiter.reset(account_key)
    return TokenResponse(access_token=access_token, expires_in=expires_in)


@router.get("/me", response_model=UserResponse)
def read_current_user(current_user: User = Depends(get_current_user)) -> User:
    return current_user
