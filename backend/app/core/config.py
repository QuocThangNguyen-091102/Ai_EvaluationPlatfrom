"""Cấu hình ứng dụng, đọc từ biến môi trường (và file .env khi chạy trên máy host).

Mọi tham số của backend đi qua đối tượng `settings` ở đây; không đọc biến môi trường rải rác.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Danh sách origin của frontend được phép gọi API, ngăn cách bằng dấu phẩy.
    cors_allowed_origins: str = "http://localhost:5173"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allowed_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
