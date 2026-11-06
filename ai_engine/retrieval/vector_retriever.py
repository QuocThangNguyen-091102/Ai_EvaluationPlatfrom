"""Tìm các chunk gần câu hỏi nhất bằng pgvector, trong phạm vi quyền của user.

Ngoại lệ có chủ đích với quy tắc "chỉ Repository truy cập DB" (docs/04_architecture.md mục 5): truy vấn vector gắn
chặt với lọc quyền nên nằm ở đây. File không import backend; caller truyền vào một SQLAlchemy Session.

Không dùng chỉ mục vector gần đúng (quét chính xác), nên kết quả đúng tuyệt đối với dữ liệu nhỏ và việc lọc theo
user không làm mất kết quả (R10). Thêm chỉ mục khi đo thấy chậm.
"""

import uuid
from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy import bindparam, text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Session

from ai_engine.retrieval.metadata_filters import RetrievalScope, build_scope_filter


@dataclass(frozen=True)
class RetrievedChunk:
    rank: int
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    # Hash nội dung của tài liệu: dùng để so với reference context của dataset (ổn định qua các lần reprocess).
    document_content_hash: str
    filename: str
    page_number: int | None
    chunk_index: int
    char_start: int
    char_end: int
    content: str
    # Cosine similarity trong [-1, 1]; vector đã chuẩn hóa nên bằng 1 - khoảng cách cosine.
    score: float


def _vector_literal(vector: Sequence[float]) -> str:
    return "[" + ",".join(repr(float(v)) for v in vector) + "]"


def retrieve(session: Session, query_vector: Sequence[float], scope: RetrievalScope, *, top_k: int) -> list[RetrievedChunk]:
    if top_k < 1:
        raise ValueError("top_k phải ít nhất là 1")
    where, params = build_scope_filter(scope)
    statement = text(
        f"""
        SELECT c.id, c.document_id, d.content_hash, d.filename, c.page_number, c.chunk_index, c.char_start, c.char_end, c.content,
               1 - (c.embedding <=> CAST(:query_vector AS vector)) AS score
        FROM document_chunks AS c
        JOIN documents AS d ON d.id = c.document_id AND d.user_id = c.user_id
        WHERE {where}
        ORDER BY c.embedding <=> CAST(:query_vector AS vector), c.id
        LIMIT :top_k
        """
    )
    if "document_ids" in params:
        statement = statement.bindparams(bindparam("document_ids", type_=ARRAY(UUID(as_uuid=True))))
    rows = session.execute(statement, {**params, "query_vector": _vector_literal(query_vector), "top_k": top_k}).all()
    return [
        RetrievedChunk(
            rank=rank,
            chunk_id=row.id,
            document_id=row.document_id,
            document_content_hash=row.content_hash,
            filename=row.filename,
            page_number=row.page_number,
            chunk_index=row.chunk_index,
            char_start=row.char_start,
            char_end=row.char_end,
            content=row.content,
            score=float(row.score),
        )
        for rank, row in enumerate(rows, start=1)
    ]
