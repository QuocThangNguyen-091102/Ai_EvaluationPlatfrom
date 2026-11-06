import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

QuestionType = Literal["fact", "multi_hop", "summarization", "unanswerable"]
Difficulty = Literal["easy", "medium", "hard"]
ExpectedBehavior = Literal["answer", "insufficient_context"]


class DatasetCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    description: str | None = Field(default=None, max_length=2000)


class DatasetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None
    created_at: datetime


class DatasetListResponse(BaseModel):
    items: list[DatasetResponse]
    total: int
    limit: int
    offset: int


class VersionCreate(BaseModel):
    copy_from_version_id: uuid.UUID | None = None
    notes: str | None = Field(default=None, max_length=2000)


class DatasetVersionResponse(BaseModel):
    id: uuid.UUID
    dataset_id: uuid.UUID
    version_number: int
    status: str
    reviewed_at: datetime | None
    notes: str | None
    created_at: datetime
    test_case_count: int


class DatasetVersionListResponse(BaseModel):
    items: list[DatasetVersionResponse]


class ReferenceInput(BaseModel):
    """Chọn tài liệu bằng document_id hoặc filename, và chép nguyên văn câu trích chứa đáp án."""

    document_id: uuid.UUID | None = None
    filename: str | None = Field(default=None, max_length=255)
    quote: str = Field(min_length=3, max_length=2000)

    @model_validator(mode="after")
    def has_document(self):
        if self.document_id is None and not self.filename:
            raise ValueError("Cần document_id hoặc filename")
        return self


class TestCaseInput(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    ground_truth_answer: str | None = Field(default=None, max_length=4000)
    reference_contexts: list[ReferenceInput] = Field(default_factory=list, max_length=10)
    source_note: str | None = Field(default=None, max_length=1000)
    question_type: QuestionType
    difficulty: Difficulty
    expected_behavior: ExpectedBehavior


class ReferenceContextResponse(BaseModel):
    document_content_hash: str
    filename: str
    char_start: int
    char_end: int
    text: str


class TestCaseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    dataset_version_id: uuid.UUID
    question: str
    ground_truth_answer: str | None
    reference_contexts: list[ReferenceContextResponse]
    source_note: str | None
    question_type: str
    difficulty: str
    expected_behavior: str
    created_at: datetime


class TestCaseListResponse(BaseModel):
    items: list[TestCaseResponse]
    total: int
    limit: int
    offset: int


class ImportResult(BaseModel):
    imported: int
