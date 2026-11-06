"""Biến các chunk truy xuất được thành khối ngữ cảnh đánh số cho prompt, và đọc lại trích dẫn [n] từ câu trả lời."""

import re
from collections.abc import Sequence

from ai_engine.generation.prompt_templates import ContextBlock
from ai_engine.pipeline.rag_result import Citation
from ai_engine.retrieval.vector_retriever import RetrievedChunk

_CITATION = re.compile(r"\[(\d+)\]")


def build_context_blocks(chunks: Sequence[RetrievedChunk]) -> list[ContextBlock]:
    return [
        ContextBlock(number=index, source=chunk.filename, page_number=chunk.page_number, text=chunk.content)
        for index, chunk in enumerate(chunks, start=1)
    ]


def cited_numbers(answer: str, source_count: int) -> list[int]:
    """Các số [n] hợp lệ trong câu trả lời, theo thứ tự xuất hiện lần đầu. Số ngoài phạm vi bị bỏ (LLM bịa nguồn)."""
    seen: list[int] = []
    for match in _CITATION.finditer(answer):
        number = int(match.group(1))
        if 1 <= number <= source_count and number not in seen:
            seen.append(number)
    return seen


def extract_citations(answer: str, chunks: Sequence[RetrievedChunk]) -> list[Citation]:
    return [Citation(number=number, chunk=chunks[number - 1]) for number in cited_numbers(answer, len(chunks))]
