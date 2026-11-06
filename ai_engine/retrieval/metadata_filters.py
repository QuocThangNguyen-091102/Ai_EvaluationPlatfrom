"""Dựng điều kiện lọc quyền cho truy vấn vector.

Lọc theo user là BẮT BUỘC và nằm trong câu SQL, không lọc sau khi lấy kết quả: nếu lọc sau, kết quả Top-K có thể
đã chứa chunk của người khác (rò rỉ qua điểm số, thời gian) hoặc bị thiếu.
"""

import uuid
from collections.abc import Sequence
from dataclasses import dataclass, field


@dataclass(frozen=True)
class RetrievalScope:
    user_id: uuid.UUID
    # None: mọi tài liệu của user; danh sách: chỉ các tài liệu này (vẫn phải thuộc user).
    document_ids: Sequence[uuid.UUID] | None = field(default=None)

    def __post_init__(self) -> None:
        if not isinstance(self.user_id, uuid.UUID):
            raise ValueError("Truy xuất bắt buộc có user_id hợp lệ")
        if self.document_ids is not None and len(self.document_ids) == 0:
            raise ValueError("document_ids rỗng: không có tài liệu nào để tìm")


def build_scope_filter(scope: RetrievalScope) -> tuple[str, dict]:
    """Trả (đoạn SQL điều kiện, tham số). Mọi giá trị đi qua tham số, không ghép chuỗi."""
    conditions = ["c.user_id = :user_id", "d.user_id = :user_id", "d.status = 'ready'"]
    params: dict = {"user_id": scope.user_id}
    if scope.document_ids is not None:
        conditions.append("c.document_id = ANY(:document_ids)")
        params["document_ids"] = list(scope.document_ids)
    return " AND ".join(conditions), params
