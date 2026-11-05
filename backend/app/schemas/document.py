import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


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
