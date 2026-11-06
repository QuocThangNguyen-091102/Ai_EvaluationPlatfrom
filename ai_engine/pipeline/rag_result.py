from dataclasses import dataclass
from decimal import Decimal

from ai_engine.retrieval.vector_retriever import RetrievedChunk


@dataclass(frozen=True)
class Citation:
    # Số [n] xuất hiện trong câu trả lời, trỏ tới contexts[n - 1].
    number: int
    chunk: RetrievedChunk


@dataclass(frozen=True)
class RagResult:
    answer: str
    insufficient_context: bool
    # Mọi chunk đã đưa cho bước sinh câu trả lời (theo thứ tự [1], [2], ...).
    contexts: list[RetrievedChunk]
    # Chỉ các chunk được câu trả lời trích dẫn thật.
    citations: list[Citation]
    mode: str  # "llm" hoặc "extractive"
    llm_provider: str
    llm_model: str
    prompt_version: str
    latency_ms: int
    prompt_tokens: int | None
    completion_tokens: int | None
    estimated_cost: Decimal | None
