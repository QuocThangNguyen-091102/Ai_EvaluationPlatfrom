import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.core.config import settings

# Giới hạn trên để chặn việc gửi mật khẩu cực dài làm tốn tài nguyên khi băm.
_PASSWORD_MAX_LENGTH = 128


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(max_length=_PASSWORD_MAX_LENGTH)

    @field_validator("password")
    @classmethod
    def password_long_enough(cls, value: str) -> str:
        if len(value) < settings.password_min_length:
            raise ValueError(f"Mật khẩu phải có ít nhất {settings.password_min_length} ký tự")
        return value


class LoginRequest(BaseModel):
    # Không kiểm tra định dạng chặt ở đây: sai thông tin phải trả cùng một thông báo chung.
    email: str = Field(min_length=1, max_length=320)
    password: str = Field(min_length=1, max_length=_PASSWORD_MAX_LENGTH)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
