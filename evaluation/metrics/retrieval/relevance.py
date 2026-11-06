"""Gán nhãn liên quan cho các chunk truy xuất được, so với reference contexts của test case.

Một chunk LIÊN QUAN khi thuộc đúng tài liệu (so bằng content hash) và khoảng ký tự của nó chồng lên khoảng của ít
nhất một reference. Vị trí ký tự của chunk và của reference cùng tính trên văn bản đã làm sạch của tài liệu, nên so
được với nhau dù chunk size thay đổi.
"""

from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class Span:
    document_hash: str
    start: int
    end: int

    def overlaps(self, other: "Span") -> bool:
        return self.document_hash == other.document_hash and self.start < other.end and other.start < self.end


@dataclass(frozen=True)
class RelevanceLabels:
    # relevant[i]: chunk ở hạng i + 1 có chồng lên reference nào không.
    relevant: list[bool]
    # covered[i]: tập chỉ số reference mà chunk hạng i + 1 chồng lên.
    covered: list[frozenset[int]]
    reference_count: int


def label_relevance(retrieved: Sequence[Span], references: Sequence[Span]) -> RelevanceLabels:
    covered = [frozenset(i for i, ref in enumerate(references) if chunk.overlaps(ref)) for chunk in retrieved]
    return RelevanceLabels(relevant=[bool(c) for c in covered], covered=covered, reference_count=len(references))
