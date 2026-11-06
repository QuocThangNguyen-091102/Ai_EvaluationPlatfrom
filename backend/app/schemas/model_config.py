import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ModelConfigurationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    llm_provider: str = Field(min_length=1, max_length=50)
    llm_model: str = Field(min_length=1, max_length=100)
    prompt_version: str | None = Field(default=None, max_length=50)
    top_k: int | None = Field(default=None, ge=1, le=20)
    temperature: float | None = Field(default=None, ge=0, le=2)
    # Mặc định lấy theo máy chủ; chỉ chấp nhận đúng model embedding đang dùng vì vector trong DB cố định số chiều.
    embedding_provider: str | None = None
    embedding_model: str | None = None
    chunk_size: int | None = Field(default=None, ge=20, le=400)
    chunk_overlap: int | None = Field(default=None, ge=0, le=200)

    @model_validator(mode="after")
    def overlap_smaller_than_size(self):
        if self.chunk_size is not None and self.chunk_overlap is not None and self.chunk_overlap >= self.chunk_size:
            raise ValueError("chunk_overlap phải nhỏ hơn chunk_size")
        return self


class ModelConfigurationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    llm_provider: str
    llm_model: str
    embedding_provider: str
    embedding_model: str
    prompt_version: str
    top_k: int
    temperature: float
    chunk_size: int
    chunk_overlap: int
    created_at: datetime


class ModelConfigurationListResponse(BaseModel):
    items: list[ModelConfigurationResponse]
    total: int
    limit: int
    offset: int


class ServerCapabilities(BaseModel):
    """Những gì máy chủ hỗ trợ, để giao diện chỉ cho chọn giá trị hợp lệ."""

    llm_configured: bool
    llm_provider: str | None
    default_llm_model: str | None
    embedding_provider: str
    embedding_model: str
    prompt_versions: list[str]
