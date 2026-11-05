import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKeyConstraint, Index, String, Text, UniqueConstraint, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base

# Số chiều vector do embedding model quyết định (docs/06_deployment_tech.md mục 4).
# Đổi model có số chiều khác nghĩa là phải có migration mới và embed lại toàn bộ chunk.
EMBEDDING_DIMENSIONS = 384


class DocumentChunk(Base):
    """Đơn vị truy xuất của RAG: văn bản của chunk và vector của nó (cùng một hàng)."""

    __tablename__ = "document_chunks"
    __table_args__ = (
        # Khóa ngoại kép: DB bảo đảm chunk.user_id luôn bằng document.user_id (rào chắn thứ hai cho cô lập dữ liệu).
        ForeignKeyConstraint(
            ["document_id", "user_id"],
            ["documents.id", "documents.user_id"],
            ondelete="CASCADE",
            name="fk_document_chunks_document_id_user_id",
        ),
        UniqueConstraint("document_id", "chunk_index", name="uq_document_chunks_document_id_chunk_index"),
        Index("ix_document_chunks_user_id", "user_id"),
        # Chưa tạo chỉ mục vector (HNSW, IVFFlat). Với dữ liệu nhỏ, quét chính xác cho kết quả đúng và tránh
        # việc lọc theo user_id làm chỉ mục gần đúng trả thiếu. Thêm chỉ mục khi đã đo được nhu cầu (M4).
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    document_id: Mapped[uuid.UUID]
    # Sao chép từ document để lọc quyền ngay trong truy vấn vector, không cần join.
    user_id: Mapped[uuid.UUID]
    chunk_index: Mapped[int]
    content: Mapped[str] = mapped_column(Text)
    page_number: Mapped[int | None]
    char_start: Mapped[int]
    char_end: Mapped[int]
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIMENSIONS))
    # Để phát hiện chunk nào được embed bằng model khác (không so sánh được với nhau).
    embedding_model: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
