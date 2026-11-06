import uuid
from collections.abc import Sequence

from sqlalchemy import delete
from sqlalchemy.orm import Session

from ai_engine.ingestion.ingestion_pipeline import EmbeddedChunk
from app.models.document_chunk import DocumentChunk


class ChunkRepository:
    """Nơi duy nhất ghi bảng document_chunks."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def replace_chunks(
        self, *, user_id: uuid.UUID, document_id: uuid.UUID, chunks: Sequence[EmbeddedChunk], embedding_model: str
    ) -> None:
        """Xóa chunk cũ rồi ghi chunk mới trong transaction hiện tại (caller commit), để reprocess không tạo trùng."""
        self._session.execute(
            delete(DocumentChunk).where(DocumentChunk.document_id == document_id, DocumentChunk.user_id == user_id)
        )
        self._session.add_all(
            DocumentChunk(
                document_id=document_id,
                user_id=user_id,
                chunk_index=item.chunk.index,
                content=item.chunk.content,
                page_number=item.chunk.page_number,
                char_start=item.chunk.char_start,
                char_end=item.chunk.char_end,
                embedding=item.embedding,
                embedding_model=embedding_model,
            )
            for item in chunks
        )
        self._session.flush()
