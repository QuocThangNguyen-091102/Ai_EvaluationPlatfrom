import hashlib
import logging
import uuid
from typing import BinaryIO

from app.core.config import settings
from app.core.exceptions import AppError
from app.core.file_storage import build_storage_path, delete_file, save_file
from app.core.file_validation import UnsupportedFileTypeError, detect_file_type, sanitize_display_name
from app.models.document import Document
from app.models.user import User
from app.repositories.document_repository import DocumentRepository, DuplicateDocumentError

logger = logging.getLogger(__name__)

_READ_CHUNK_BYTES = 1024 * 1024


class DocumentService:
    """Use case upload tài liệu. Parse, chunk, embed được thêm ở M3-T04 đến M3-T07."""

    def __init__(self, documents: DocumentRepository) -> None:
        self._documents = documents

    def upload(self, user: User, filename: str | None, stream: BinaryIO) -> Document:
        content = self._read_with_limit(stream)
        if not content:
            raise AppError(422, "validation_error", "File rỗng")

        try:
            detected = detect_file_type(filename, content)
        except UnsupportedFileTypeError as exc:
            raise AppError(415, "unsupported_file_type", str(exc)) from None

        content_hash = hashlib.sha256(content).hexdigest()
        existing = self._documents.find_by_hash(user.id, content_hash)
        if existing is not None:
            raise self._duplicate_error(existing.id)

        document_id = uuid.uuid4()
        storage_path = build_storage_path(user.id, document_id, detected.extension)
        document = Document(
            id=document_id,
            user_id=user.id,
            filename=sanitize_display_name(filename),
            content_type=detected.content_type,
            size_bytes=len(content),
            content_hash=content_hash,
            storage_path=storage_path,
            status="uploaded",
        )

        try:
            self._documents.add(document)
        except DuplicateDocumentError:
            # Hai request upload cùng nội dung chạy song song: request đến sau thua ở ràng buộc duy nhất.
            existing = self._documents.find_by_hash(user.id, content_hash)
            raise self._duplicate_error(existing.id if existing else None) from None

        try:
            save_file(storage_path, content)
            self._documents.commit()
        except Exception:
            # Không để lại bản ghi "ma" trỏ tới file không tồn tại, cũng không để lại file mồ côi.
            self._documents.rollback()
            self._remove_quietly(storage_path)
            raise

        self._documents.refresh(document)
        logger.info("Document uploaded: id=%s user_id=%s size_bytes=%s", document.id, user.id, document.size_bytes)
        return document

    def count_chunks(self, user: User, document: Document) -> int:
        return self._documents.count_chunks(user.id, document.id)

    def list_documents(
        self, user: User, *, status: str | None, limit: int, offset: int
    ) -> tuple[list[tuple[Document, int]], int]:
        return self._documents.list_for_user(user.id, status=status, limit=limit, offset=offset)

    def get_document(self, user: User, document_id: uuid.UUID) -> tuple[Document, int]:
        document = self._documents.get_for_user(user.id, document_id)
        if document is None:
            # Cùng một thông báo cho "không tồn tại" và "thuộc user khác" để không lộ sự tồn tại.
            raise AppError(404, "not_found", "Không tìm thấy tài liệu")
        return document, self._documents.count_chunks(user.id, document.id)

    def delete_document(self, user: User, document_id: uuid.UUID) -> None:
        document, _ = self.get_document(user, document_id)
        storage_path = document.storage_path
        self._documents.delete(document)
        # Xóa bản ghi trước, file sau: nếu xóa file lỗi chỉ còn một file thừa vô hại, không có bản ghi trỏ vào file mất.
        self._remove_quietly(storage_path)
        logger.info("Document deleted: id=%s user_id=%s", document_id, user.id)

    def _read_with_limit(self, stream: BinaryIO) -> bytes:
        limit = settings.max_upload_size_mb * 1024 * 1024
        parts: list[bytes] = []
        total = 0
        while True:
            chunk = stream.read(_READ_CHUNK_BYTES)
            if not chunk:
                break
            total += len(chunk)
            if total > limit:
                raise AppError(
                    413,
                    "file_too_large",
                    f"File vượt quá giới hạn {settings.max_upload_size_mb} MB",
                )
            parts.append(chunk)
        return b"".join(parts)

    @staticmethod
    def _duplicate_error(existing_document_id: uuid.UUID | None) -> AppError:
        return AppError(
            409,
            "conflict",
            "Bạn đã upload tài liệu có cùng nội dung",
            details={"existing_document_id": str(existing_document_id) if existing_document_id else None},
        )

    @staticmethod
    def _remove_quietly(storage_path: str) -> None:
        try:
            delete_file(storage_path)
        except OSError:
            logger.warning("Could not remove file after failed upload: %s", storage_path)
