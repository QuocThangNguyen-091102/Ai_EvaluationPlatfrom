import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class DocumentResponse(BaseModel):
    """Hình dạng document trả về cho client (xem docs/08_api_contracts.md mục 4)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    filename: str
    content_type: str
    size_bytes: int
    status: str
    error_message: str | None
    # Không phải cột của bảng documents: router điền từ số chunk thật trong DB.
    chunk_count: int = 0
    processing_config: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime


class DocumentListResponse(BaseModel):
    items: list[DocumentResponse]
    total: int
    limit: int
    offset: int


class ReprocessRequest(BaseModel):
    """Để trống thì dùng giá trị mặc định ở configs/rag_default.yaml. Đơn vị là từ."""

    chunk_size: int | None = Field(default=None, ge=20, le=400)
    chunk_overlap: int | None = Field(default=None, ge=0, le=200)

    @model_validator(mode="after")
    def overlap_smaller_than_size(self):
        if self.chunk_size is not None and self.chunk_overlap is not None and self.chunk_overlap >= self.chunk_size:
            raise ValueError("chunk_overlap phải nhỏ hơn chunk_size")
        return self
