"""Bản giả dùng trong test, cài đúng interface của ai_engine nên thay được bản thật."""

import hashlib
import math
import re
from collections.abc import Sequence

from ai_engine.embeddings.base_embedder import Embedder, EmbeddingError
from ai_engine.generation.base_llm_client import LlmClient, LlmMessage, LlmResult

_WORD = re.compile(r"\w+", re.UNICODE)


class HashEmbedder(Embedder):
    """Vector "túi từ": mỗi từ băm vào một chiều. Hai văn bản chung nhiều từ thì cosine cao.

    Không hiểu nghĩa như model thật, nhưng xác định (deterministic) và đủ để test truy xuất có thứ tự đúng.
    """

    def __init__(self, dimensions: int = 384, fail_with: Exception | None = None) -> None:
        self._dimensions = dimensions
        self._fail_with = fail_with
        self.passage_calls: list[list[str]] = []

    @property
    def model_name(self) -> str:
        return "test-hash-embedder"

    @property
    def dimensions(self) -> int:
        return self._dimensions

    def embed_passages(self, texts: Sequence[str]) -> list[list[float]]:
        if self._fail_with is not None:
            raise self._fail_with
        self.passage_calls.append(list(texts))
        return [self._vector(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        if self._fail_with is not None:
            raise self._fail_with
        return self._vector(text)

    def _vector(self, text: str) -> list[float]:
        vector = [0.0] * self._dimensions
        for word in _WORD.findall(text.lower()):
            index = int(hashlib.sha256(word.encode()).hexdigest(), 16) % self._dimensions
            vector[index] += 1.0
        norm = math.sqrt(sum(v * v for v in vector)) or 1.0
        if norm == 1.0 and not any(vector):
            vector[0] = 1.0  # văn bản không có từ nào: vector đơn vị cố định thay vì vector 0
            return vector
        return [v / norm for v in vector]


class ScriptedLlm(LlmClient):
    """LLM giả: trả lời theo hàm `respond(messages)` và ghi lại mọi lần gọi."""

    def __init__(self, respond=None, *, prompt_tokens: int | None = 100, completion_tokens: int | None = 20) -> None:
        self._respond = respond or (lambda messages: "Câu trả lời giả [1]")
        self._prompt_tokens = prompt_tokens
        self._completion_tokens = completion_tokens
        self.calls: list[list[LlmMessage]] = []

    @property
    def provider_name(self) -> str:
        return "test"

    @property
    def model_name(self) -> str:
        return "scripted"

    def generate(self, messages, *, temperature, max_tokens=None) -> LlmResult:
        self.calls.append(list(messages))
        reply = self._respond(messages)
        if isinstance(reply, Exception):
            raise reply
        return LlmResult(text=reply, prompt_tokens=self._prompt_tokens, completion_tokens=self._completion_tokens)


__all__ = ["EmbeddingError", "HashEmbedder", "ScriptedLlm"]
