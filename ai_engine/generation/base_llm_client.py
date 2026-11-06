"""Hợp đồng của mọi LLM provider. Pipeline và LLM judge chỉ biết hợp đồng này."""

from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

Role = Literal["system", "user", "assistant"]


@dataclass(frozen=True)
class LlmMessage:
    role: Role
    content: str


@dataclass(frozen=True)
class LlmResult:
    text: str
    # None khi provider không báo số token (không đoán).
    prompt_tokens: int | None
    completion_tokens: int | None


class LlmError(Exception):
    """Provider không trả được câu trả lời. Thông điệp an toàn: không chứa API key hay nội dung prompt."""


class LlmTransientError(LlmError):
    """Lỗi tạm thời (timeout, mất kết nối, lỗi 5xx): đáng thử lại."""


class LlmRateLimitError(LlmTransientError):
    """Provider từ chối vì vượt hạn mức tần suất."""

    def __init__(self, message: str, retry_after_seconds: float | None = None) -> None:
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds


class LlmClient(ABC):
    @property
    @abstractmethod
    def provider_name(self) -> str: ...

    @property
    @abstractmethod
    def model_name(self) -> str: ...

    @abstractmethod
    def generate(
        self, messages: Sequence[LlmMessage], *, temperature: float, max_tokens: int | None = None
    ) -> LlmResult: ...
