"""Tìm vị trí (char_start, char_end) của một câu trích trong văn bản đã làm sạch của tài liệu.

Văn bản được dựng lại từ các chunk (mỗi chunk biết vị trí của mình), nên không cần lưu riêng toàn văn. So khớp sau
khi gộp khoảng trắng và chuẩn hóa NFC, vì người viết dataset thường chép câu trích với xuống dòng khác bản gốc.
"""

import re
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass

_WHITESPACE = re.compile(r"\s+")


@dataclass(frozen=True)
class ChunkSpan:
    char_start: int
    char_end: int
    content: str


class QuoteNotFoundError(ValueError):
    pass


class AmbiguousQuoteError(ValueError):
    pass


def rebuild_text(chunks: Sequence[ChunkSpan]) -> str:
    """Dựng lại văn bản theo vị trí của chunk; khoảng hở giữa các chunk (chỉ là khoảng trắng) điền bằng dấu cách."""
    if not chunks:
        return ""
    buffer = [" "] * max(chunk.char_end for chunk in chunks)
    for chunk in chunks:
        buffer[chunk.char_start : chunk.char_end] = chunk.content
    return "".join(buffer)


def _normalize_with_map(text: str) -> tuple[str, list[int]]:
    """Gộp mọi chuỗi khoảng trắng thành một dấu cách; trả kèm vị trí gốc của từng ký tự trong chuỗi kết quả."""
    normalized: list[str] = []
    positions: list[int] = []
    previous_space = True
    for index, char in enumerate(text):
        if char.isspace():
            if not previous_space:
                normalized.append(" ")
                positions.append(index)
            previous_space = True
        else:
            normalized.append(char)
            positions.append(index)
            previous_space = False
    return "".join(normalized), positions


def normalize_quote(quote: str) -> str:
    return _WHITESPACE.sub(" ", unicodedata.normalize("NFC", quote)).strip()


def locate_quote(chunks: Sequence[ChunkSpan], quote: str) -> tuple[int, int, str]:
    """Trả (char_start, char_end, đoạn văn bản gốc). Báo lỗi nếu không tìm thấy hoặc xuất hiện nhiều lần."""
    needle = normalize_quote(quote)
    if not needle:
        raise QuoteNotFoundError("Câu trích rỗng")
    text = rebuild_text(chunks)
    haystack, positions = _normalize_with_map(unicodedata.normalize("NFC", text))

    first = haystack.find(needle)
    if first == -1:
        raise QuoteNotFoundError("Không tìm thấy câu trích trong tài liệu (hãy chép nguyên văn)")
    if haystack.find(needle, first + 1) != -1:
        raise AmbiguousQuoteError("Câu trích xuất hiện nhiều lần trong tài liệu; hãy trích dài hơn để xác định duy nhất")

    start = positions[first]
    end = positions[first + len(needle) - 1] + 1
    return start, end, text[start:end]
