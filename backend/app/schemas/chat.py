import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    session_id: uuid.UUID | None = None
    model_configuration_id: uuid.UUID | None = None


class CitationResponse(BaseModel):
    number: int
    chunk_id: uuid.UUID | None
    filename: str
    page_number: int | None
    score: float
    snippet: str


class AnswerMetrics(BaseModel):
    latency_ms: int | None
    prompt_tokens: int | None
    completion_tokens: int | None
    estimated_cost: Decimal | None


class ChatAnswerResponse(BaseModel):
    session_id: uuid.UUID
    message_id: uuid.UUID
    answer: str
    insufficient_context: bool
    mode: str
    citations: list[CitationResponse]
    # Mọi đoạn đã đưa cho bước sinh câu trả lời (kể cả không được trích dẫn), để người dùng tự kiểm tra.
    sources: list[CitationResponse]
    metrics: AnswerMetrics
    model_configuration_id: uuid.UUID


class ChatSessionResponse(BaseModel):
    id: uuid.UUID
    title: str
    created_at: datetime


class ChatSessionListResponse(BaseModel):
    items: list[ChatSessionResponse]
    total: int
    limit: int
    offset: int


class ChatMessageResponse(BaseModel):
    id: uuid.UUID
    role: str
    content: str
    created_at: datetime
    insufficient_context: bool
    model_configuration_id: uuid.UUID | None
    error_message: str | None
    citations: list[CitationResponse]
    sources: list[CitationResponse]
    metrics: AnswerMetrics


class ChatMessageListResponse(BaseModel):
    items: list[ChatMessageResponse]
