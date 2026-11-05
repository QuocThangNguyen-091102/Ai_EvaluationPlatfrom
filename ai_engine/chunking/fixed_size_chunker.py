"""Chia văn bản thành các chunk có kích thước cố định (tính bằng TỪ) và có phần chồng (overlap).

Đơn vị là từ (chuỗi ký tự không phải khoảng trắng), không phải ký tự hay token của model, để chunker độc lập với
embedding model. Model e5 chỉ nhận tối đa 512 token và cắt âm thầm phần vượt; embedder (M3-T06) phải kiểm tra
độ dài thật bằng token. Mẫu đo cho thấy khoảng 1,2 token mỗi từ tiếng Việt, nên chunk_size theo từ cần nhỏ hơn
512 một khoảng an toàn.
"""

import bisect
import re
from dataclasses import dataclass

from ai_engine.ingestion.parsed_document import ParsedDocument

_WORD = re.compile(r"\S+")
_PAGE_SEPARATOR = "\n\n"


@dataclass(frozen=True)
class Chunk:
    index: int
    content: str
    # Trang chứa từ đầu tiên của chunk; None với định dạng không có trang.
    page_number: int | None
    # Vị trí trong văn bản đầy đủ của tài liệu (các trang nối bằng dòng trống): full_text[char_start:char_end] == content.
    char_start: int
    char_end: int
    word_count: int


def full_text(document: ParsedDocument) -> str:
    """Văn bản đầy đủ mà char_start và char_end của chunk tham chiếu tới."""
    return _PAGE_SEPARATOR.join(page.text for page in document.pages)


def chunk_document(document: ParsedDocument, *, chunk_size: int, overlap: int) -> list[Chunk]:
    """Chia tài liệu (đã làm sạch) thành các chunk dài `chunk_size` từ, hai chunk liền nhau chung `overlap` từ."""
    if chunk_size < 1:
        raise ValueError("chunk_size phải lớn hơn 0")
    if not 0 <= overlap < chunk_size:
        raise ValueError("overlap phải từ 0 đến nhỏ hơn chunk_size")

    text = full_text(document)
    spans = [match.span() for match in _WORD.finditer(text)]
    if not spans:
        return []

    page_starts, page_numbers = _page_offsets(document)
    step = chunk_size - overlap
    chunks: list[Chunk] = []
    start = 0
    while True:
        end = min(start + chunk_size, len(spans))
        char_start = spans[start][0]
        char_end = spans[end - 1][1]
        page_index = bisect.bisect_right(page_starts, char_start) - 1
        chunks.append(
            Chunk(
                index=len(chunks),
                content=text[char_start:char_end],
                page_number=page_numbers[page_index],
                char_start=char_start,
                char_end=char_end,
                word_count=end - start,
            )
        )
        if end == len(spans):
            return chunks
        start += step


def _page_offsets(document: ParsedDocument) -> tuple[list[int], list[int | None]]:
    starts: list[int] = []
    numbers: list[int | None] = []
    offset = 0
    for page in document.pages:
        starts.append(offset)
        numbers.append(page.page_number)
        offset += len(page.text) + len(_PAGE_SEPARATOR)
    return starts, numbers
