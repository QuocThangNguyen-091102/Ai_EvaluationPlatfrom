import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

SecurityCategory = Literal["prompt_injection", "jailbreak", "data_leakage", "access_control", "malicious_documents"]


class SecurityTestCaseResponse(BaseModel):
    key: str
    version: int
    category: str
    title: str
    description: str
    severity: str
    requires_llm: bool
    expected_behavior: str
    mitigation: str
    uses_judge: bool


class SecurityTestCaseListResponse(BaseModel):
    items: list[SecurityTestCaseResponse]


class SecurityRunCreate(BaseModel):
    model_configuration_id: uuid.UUID | None = None
    # Để trống: chạy cả 5 nhóm.
    categories: list[SecurityCategory] | None = Field(default=None, min_length=1)
    judge_model: str | None = Field(default=None, min_length=1, max_length=100)


class SecurityRunResponse(BaseModel):
    id: uuid.UUID
    status: str
    model_configuration_id: uuid.UUID
    categories: list[str]
    total_cases: int
    completed_cases: int
    judge_model: str | None
    judge_prompt_version: str | None
    summary: dict[str, Any]
    coverage_notes: list[str]
    environment: dict[str, Any]
    error_message: str | None
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime


class SecurityRunListResponse(BaseModel):
    items: list[SecurityRunResponse]
    total: int
    limit: int
    offset: int


class SecurityContextResponse(BaseModel):
    rank: int
    filename: str
    score: float
    snippet: str


class SecurityResultResponse(BaseModel):
    id: uuid.UUID
    test_case_id: uuid.UUID
    case_key: str
    category: str
    title: str
    description: str
    expected_behavior: str
    status: str
    severity: str
    actual_response: str | None
    evidence: dict[str, Any]
    evaluator: str
    mitigation: str
    error_message: str | None
    latency_ms: int | None
    contexts: list[SecurityContextResponse]


class SecurityResultListResponse(BaseModel):
    items: list[SecurityResultResponse]
    total: int
    limit: int
    offset: int
