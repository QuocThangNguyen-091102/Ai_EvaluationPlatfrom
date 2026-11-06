"""RAG pipeline DUY NHẤT của hệ thống. Chat, Evaluation, Benchmark và Security đều gọi `RagPipeline.run`.

Các bước: embed câu hỏi -> truy xuất trong phạm vi quyền -> dựng ngữ cảnh -> sinh câu trả lời -> đọc trích dẫn.
Không phụ thuộc FastAPI; gọi được từ script độc lập, chỉ cần một SQLAlchemy Session.

Xử lý "không đủ bằng chứng":
1. Không truy xuất được chunk nào: trả câu từ chối, không gọi LLM.
2. Có chunk nhưng không trả lời được: prompt yêu cầu LLM trả đúng câu từ chối; pipeline nhận ra câu đó.
Chưa dùng ngưỡng điểm tương đồng: điểm cosine của model bị nén ở khoảng cao (đã đo, R21) và chưa có baseline để
hiệu chỉnh ngưỡng, nên đặt ngưỡng lúc này là đặt tùy ý.
"""

import time
import uuid
from collections.abc import Callable, Sequence
from decimal import Decimal

from sqlalchemy.orm import Session

from ai_engine.embeddings.base_embedder import Embedder
from ai_engine.generation.base_llm_client import LlmClient
from ai_engine.generation.cost_estimator import PriceTable
from ai_engine.generation.prompt_templates import INSUFFICIENT_CONTEXT_ANSWER, build_answer_messages
from ai_engine.pipeline.context_builder import build_context_blocks, extract_citations
from ai_engine.pipeline.rag_config import RAGConfig
from ai_engine.pipeline.rag_result import Citation, RagResult
from ai_engine.retrieval.metadata_filters import RetrievalScope
from ai_engine.retrieval.vector_retriever import RetrievedChunk, retrieve

EXTRACTIVE_INTRO = "Hệ thống chưa cấu hình LLM nên chỉ hiển thị các đoạn tài liệu liên quan nhất:"
_SNIPPET_WORDS = 60


class RagPipeline:
    def __init__(
        self,
        *,
        embedder: Embedder,
        llm_for: Callable[[RAGConfig], LlmClient],
        price_table: PriceTable,
        clock: Callable[[], float] = time.perf_counter,
    ) -> None:
        self._embedder = embedder
        self._llm_for = llm_for
        self._price_table = price_table
        self._clock = clock

    def run(
        self,
        session: Session,
        *,
        question: str,
        user_id: uuid.UUID,
        config: RAGConfig,
        document_ids: Sequence[uuid.UUID] | None = None,
    ) -> RagResult:
        started = self._clock()
        question = question.strip()
        if not question:
            raise ValueError("Câu hỏi rỗng")

        query_vector = self._embedder.embed_query(question)
        chunks = retrieve(session, query_vector, RetrievalScope(user_id, document_ids), top_k=config.top_k)

        if not chunks:
            return self._result(INSUFFICIENT_CONTEXT_ANSWER, True, [], [], "none", config, started, None, None)

        if not config.uses_llm:
            return self._result(_extractive_answer(chunks), False, chunks, _cite_all(chunks), "extractive", config, started, None, None)

        messages = build_answer_messages(config.prompt_version, question, build_context_blocks(chunks))
        llm = self._llm_for(config)
        generated = llm.generate(messages, temperature=config.temperature, max_tokens=config.max_answer_tokens)
        answer = generated.text
        insufficient = _is_refusal(answer)
        citations = [] if insufficient else extract_citations(answer, chunks)
        return self._result(
            answer, insufficient, chunks, citations, "llm", config, started, generated.prompt_tokens, generated.completion_tokens
        )

    def _result(self, answer, insufficient, chunks, citations, mode, config, started, prompt_tokens, completion_tokens) -> RagResult:
        # Không gọi model thì chắc chắn không tốn phí API; có gọi thì ước tính theo bảng giá (không biết giá thì None).
        cost = (
            self._price_table.estimate(config.llm_provider, config.llm_model, prompt_tokens, completion_tokens)
            if mode == "llm"
            else Decimal(0)
        )
        return RagResult(
            answer=answer,
            insufficient_context=insufficient,
            contexts=list(chunks),
            citations=citations,
            mode=mode,
            llm_provider=config.llm_provider,
            llm_model=config.llm_model,
            prompt_version=config.prompt_version,
            latency_ms=int((self._clock() - started) * 1000),
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            estimated_cost=cost,
        )


_REFUSAL = INSUFFICIENT_CONTEXT_ANSWER.rstrip(".").lower()


def _is_refusal(answer: str) -> bool:
    """Câu trả lời chỉ gồm câu từ chối (cho phép thêm vài ký tự như dấu câu hoặc trích dẫn thừa)."""
    normalized = " ".join(answer.split()).lower()
    return _REFUSAL in normalized and len(normalized) < 2 * len(_REFUSAL)


def _snippet(text: str) -> str:
    words = text.split()
    return " ".join(words[:_SNIPPET_WORDS]) + (" ..." if len(words) > _SNIPPET_WORDS else "")


def _extractive_answer(chunks: Sequence[RetrievedChunk]) -> str:
    lines = [EXTRACTIVE_INTRO]
    for number, chunk in enumerate(chunks, start=1):
        lines.append(f"[{number}] {_snippet(chunk.content)}")
    return "\n".join(lines)


def _cite_all(chunks: Sequence[RetrievedChunk]) -> list[Citation]:
    return [Citation(number=number, chunk=chunk) for number, chunk in enumerate(chunks, start=1)]
