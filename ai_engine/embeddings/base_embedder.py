"""Hợp đồng của mọi embedding provider (model cục bộ hay API).

Pipeline chỉ biết hợp đồng này, nên đổi provider hay thay bằng bản giả khi test không đụng tới pipeline.
Câu hỏi và đoạn tài liệu có hai hàm riêng vì nhiều model (như e5) xử lý hai loại này khác nhau.
"""

from abc import ABC, abstractmethod
from collections.abc import Sequence


class EmbeddingError(Exception):
    """Provider không tạo được vector. Thông điệp an toàn để hiển thị, không chứa nội dung văn bản."""


class InputTooLongError(EmbeddingError):
    """Một văn bản dài hơn giới hạn của model; model sẽ cắt âm thầm nên ta từ chối thay vì để mất nội dung."""


class Embedder(ABC):
    @property
    @abstractmethod
    def model_name(self) -> str:
        """Tên model, lưu vào document_chunks.embedding_model để biết vector nào do model nào tạo."""

    @property
    @abstractmethod
    def dimensions(self) -> int:
        """Số chiều vector; phải khớp cột vector(N) trong database."""

    @abstractmethod
    def embed_passages(self, texts: Sequence[str]) -> list[list[float]]:
        """Vector cho các đoạn tài liệu, cùng thứ tự đầu vào."""

    @abstractmethod
    def embed_query(self, text: str) -> list[float]:
        """Vector cho một câu hỏi."""
