"""Cấu hình ứng dụng, đọc từ biến môi trường (và file .env khi chạy trên máy host).

Mọi tham số của backend đi qua đối tượng `settings` ở đây; không đọc biến môi trường rải rác.
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # .env nằm ở gốc repo; chạy từ thư mục backend/ thì đọc ../.env. Trong Docker, biến được truyền trực tiếp.
    model_config = SettingsConfigDict(env_file=(".env", "../.env"), extra="ignore")

    # Ví dụ: postgresql+psycopg://user:password@host:5432/dbname
    database_url: str

    # Khóa ký JWT. Bắt buộc dài ít nhất 32 ký tự; tạo bằng: python -c "import secrets; print(secrets.token_urlsafe(48))"
    jwt_secret: str = Field(min_length=32)
    jwt_expire_minutes: int = Field(default=60, gt=0)

    # Độ dài tối thiểu của mật khẩu khi đăng ký.
    password_min_length: int = Field(default=8, ge=1)

    # Thư mục lưu file gốc người dùng upload (trong Docker là volume `uploads`) và dung lượng tối đa mỗi file.
    upload_dir: str = "uploads"
    max_upload_size_mb: int = Field(default=20, gt=0)

    log_level: str = "INFO"

    # Danh sách origin của frontend được phép gọi API, ngăn cách bằng dấu phẩy.
    cors_allowed_origins: str = "http://localhost:5173"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allowed_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
