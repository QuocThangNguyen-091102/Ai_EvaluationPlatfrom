import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field


class EvaluationCreate(BaseModel):
    dataset_version_id: uuid.UUID
    model_configuration_id: uuid.UUID | None = None
    # Để trống thì không chấm các metric cần judge (ghi rõ là "bỏ qua", không điền số).
    judge_model: str | None = Field(default=None, min_length=1, max_length=100)


class MetricResponse(BaseModel):
    metric_name: str
    k: int | None
    value: float | None
    method: str
    status: str
    details: dict[str, Any]


class EvaluationRunResponse(BaseModel):
    id: uuid.UUID
    status: str
    dataset_version_id: uuid.UUID
    model_configuration_id: uuid.UUID
    judge_model: str | None
    judge_prompt_version: str | None
    total_cases: int
    completed_cases: int
    failed_cases: int
    categories: dict[str, Any]
    aggregate_metrics: list[MetricResponse]
    environment: dict[str, Any]
    error_message: str | None
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime


class EvaluationRunListResponse(BaseModel):
    items: list[EvaluationRunResponse]
    total: int
    limit: int
    offset: int


class ResultContextResponse(BaseModel):
    rank: int
    filename: str
    page_number: int | None
    score: float
    snippet: str
    relevant: bool | None


class EvaluationResultResponse(BaseModel):
    id: uuid.UUID
    test_case_id: uuid.UUID
    question: str
    expected_behavior: str
    ground_truth_answer: str | None
    status: str
    category: str
    answer: str | None
    insufficient_context: bool | None
    mode: str | None
    error_message: str | None
    latency_ms: int | None
    prompt_tokens: int | None
    completion_tokens: int | None
    estimated_cost: Decimal | None
    metrics: list[MetricResponse]
    contexts: list[ResultContextResponse]


class EvaluationResultListResponse(BaseModel):
    items: list[EvaluationResultResponse]
    total: int
    limit: int
    offset: int
