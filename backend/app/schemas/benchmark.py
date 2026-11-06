import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from app.schemas.evaluation import MetricResponse


class BenchmarkCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    dataset_version_id: uuid.UUID
    varied_variable: Literal["llm_model", "top_k", "prompt_version"]
    model_configuration_ids: list[uuid.UUID] = Field(min_length=2, max_length=6)
    judge_model: str | None = Field(default=None, min_length=1, max_length=100)

    @field_validator("model_configuration_ids")
    @classmethod
    def distinct(cls, value: list[uuid.UUID]) -> list[uuid.UUID]:
        if len(set(value)) != len(value):
            raise ValueError("Các cấu hình phải khác nhau")
        return value


class BenchmarkVariantResponse(BaseModel):
    evaluation_run_id: uuid.UUID
    model_configuration: dict[str, Any]
    varied_value: Any
    status: str
    total_cases: int
    completed_cases: int
    failed_cases: int
    categories: dict[str, Any]
    aggregate_metrics: list[MetricResponse]
    usage: dict[str, Any]
    error_message: str | None


class BenchmarkResponse(BaseModel):
    id: uuid.UUID
    name: str
    dataset_version_id: uuid.UUID
    varied_variable: str
    status: str
    judge_model: str | None
    notes: list[str]
    error_message: str | None
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime
    variants: list[BenchmarkVariantResponse]


class BenchmarkListResponse(BaseModel):
    items: list[BenchmarkResponse]
    total: int
    limit: int
    offset: int
