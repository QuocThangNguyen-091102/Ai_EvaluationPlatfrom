"""Xử lý tài liệu ở nền: đọc file gốc -> parse -> làm sạch -> chunk -> embed -> lưu chunk và vector.

Chạy sau khi request upload đã trả về (FastAPI BackgroundTasks), nên tự mở session DB riêng. Mọi lỗi đều kết thúc
bằng trạng thái `failed` kèm lý do an toàn để hiển thị; không có lỗi nào làm sập tiến trình.

Giới hạn đã biết (R9): tác vụ nền chạy trong chính tiến trình web; backend khởi động lại thì tác vụ dở bị mất.
`recover_interrupted()` chạy lúc khởi động để đánh dấu các tài liệu đó là lỗi, người dùng bấm xử lý lại.
Giả định: chỉ một tiến trình backend (một worker uvicorn), như cấu hình hiện tại.
"""

import logging
import time
import uuid
from collections.abc import Callable
from contextlib import AbstractContextManager

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ai_engine.embeddings.base_embedder import Embedder, EmbeddingError
from ai_engine.ingestion.ingestion_pipeline import ingest
from ai_engine.ingestion.parsed_document import ParsingError
from app.core.file_storage import read_file
from app.core.rag_defaults import RagDefaults
from app.repositories.chunk_repository import ChunkRepository
from app.repositories.document_repository import DocumentRepository

logger = logging.getLogger(__name__)

INTERRUPTED_MESSAGE = "Xử lý bị gián đoạn vì máy chủ khởi động lại; hãy bấm xử lý lại"
UNEXPECTED_MESSAGE = "Lỗi hệ thống khi xử lý tài liệu; hãy thử xử lý lại"


class IngestionService:
    def __init__(
        self,
        *,
        session_factory: Callable[[], AbstractContextManager[Session]],
        embedder_provider: Callable[[], Embedder],
        defaults: RagDefaults,
    ) -> None:
        self._session_factory = session_factory
        self._embedder_provider = embedder_provider
        self._defaults = defaults

    def process(self, document_id: uuid.UUID, chunk_size: int | None = None, chunk_overlap: int | None = None) -> None:
        size = chunk_size or self._defaults.chunk_size
        overlap = self._defaults.chunk_overlap if chunk_overlap is None else chunk_overlap
        started = time.monotonic()

        with self._session_factory() as session:
            documents = DocumentRepository(session)
            document = documents.get_by_id(document_id)
            if document is None:
                logger.info("Ingestion skipped, document no longer exists: id=%s", document_id)
                return
            # Đọc các trường cần dùng trước khi commit, để không giữ transaction mở trong lúc embed lâu.
            user_id, storage_path, content_type = document.user_id, document.storage_path, document.content_type
            documents.set_status(document, "processing")
            documents.commit()

            try:
                content = read_file(storage_path)
                result = ingest(content, content_type, chunk_size=size, chunk_overlap=overlap, embedder=self._embedder_provider())
            except (ParsingError, EmbeddingError) as error:
                self._fail(documents, document_id, str(error))
                return
            except FileNotFoundError:
                self._fail(documents, document_id, "Không tìm thấy file gốc của tài liệu")
                return
            except Exception:
                logger.exception("Unexpected ingestion error: document_id=%s", document_id)
                self._fail(documents, document_id, UNEXPECTED_MESSAGE)
                return

            document = documents.get_by_id(document_id)
            if document is None:
                logger.info("Document deleted while processing: id=%s", document_id)
                return
            try:
                ChunkRepository(session).replace_chunks(
                    user_id=user_id, document_id=document_id, chunks=result.chunks, embedding_model=result.embedding_model
                )
                documents.set_status(document, "ready", processing_config=result.processing_config)
                documents.commit()
            except IntegrityError:
                # Tài liệu bị xóa đúng lúc đang ghi chunk.
                documents.rollback()
                logger.info("Document deleted while saving chunks: id=%s", document_id)
                return

        logger.info(
            "Document processed: id=%s chunks=%s seconds=%.2f", document_id, len(result.chunks), time.monotonic() - started
        )

    def recover_interrupted(self) -> int:
        with self._session_factory() as session:
            documents = DocumentRepository(session)
            count = documents.mark_unfinished_as_failed(INTERRUPTED_MESSAGE)
            documents.commit()
        if count:
            logger.warning("Marked %s interrupted documents as failed", count)
        return count

    @staticmethod
    def _fail(documents: DocumentRepository, document_id: uuid.UUID, message: str) -> None:
        documents.rollback()
        document = documents.get_by_id(document_id)
        if document is None:
            return
        documents.set_status(document, "failed", error_message=message)
        documents.commit()
        logger.info("Document processing failed: id=%s", document_id)
