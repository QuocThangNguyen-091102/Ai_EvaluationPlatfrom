"""Embedding bằng model chạy cục bộ (sentence-transformers), không cần API key.

Model mặc định: intfloat/multilingual-e5-small (384 chiều, tối đa 512 token, có tiếng Việt).
Model e5 yêu cầu tiền tố "query: " cho câu hỏi và "passage: " cho đoạn tài liệu.
"""

import threading
from collections.abc import Callable, Sequence
from typing import Any

from ai_engine.embeddings.base_embedder import Embedder, EmbeddingError, InputTooLongError

DEFAULT_MODEL_NAME = "intfloat/multilingual-e5-small"
DEFAULT_DIMENSIONS = 384
QUERY_PREFIX = "query: "
PASSAGE_PREFIX = "passage: "


def _load_sentence_transformer(model_name: str, device: str) -> Any:
    # Import muộn: chỉ nạp PyTorch khi thật sự cần embed, để import module này không tốn vài giây.
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(model_name, device=device)


class LocalEmbedder(Embedder):
    def __init__(
        self,
        model_name: str = DEFAULT_MODEL_NAME,
        *,
        dimensions: int = DEFAULT_DIMENSIONS,
        batch_size: int = 16,
        device: str = "cpu",
        model_loader: Callable[[str, str], Any] = _load_sentence_transformer,
    ) -> None:
        self._model_name = model_name
        self._dimensions = dimensions
        self._batch_size = batch_size
        self._device = device
        self._model_loader = model_loader
        self._model: Any = None
        self._load_lock = threading.Lock()

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def dimensions(self) -> int:
        return self._dimensions

    def embed_passages(self, texts: Sequence[str]) -> list[list[float]]:
        return self._embed([PASSAGE_PREFIX + text for text in texts])

    def embed_query(self, text: str) -> list[float]:
        return self._embed([QUERY_PREFIX + text])[0]

    def _embed(self, prefixed_texts: list[str]) -> list[list[float]]:
        if not prefixed_texts:
            return []
        model = self._get_model()
        self._reject_texts_over_the_limit(model, prefixed_texts)
        try:
            vectors = model.encode(
                prefixed_texts,
                batch_size=self._batch_size,
                normalize_embeddings=True,
                convert_to_numpy=True,
                show_progress_bar=False,
            )
        except Exception:
            raise EmbeddingError("Model embedding gặp lỗi khi tạo vector") from None
        return [[float(value) for value in vector] for vector in vectors]

    def _get_model(self) -> Any:
        if self._model is None:
            with self._load_lock:
                if self._model is None:
                    try:
                        model = self._model_loader(self._model_name, self._device)
                    except Exception:
                        raise EmbeddingError(f"Không nạp được model embedding {self._model_name}") from None
                    self._check_dimensions(model)
                    self._model = model
        return self._model

    def _check_dimensions(self, model: Any) -> None:
        actual = model.get_embedding_dimension()
        if actual != self._dimensions:
            # Vector khác số chiều với cột trong database sẽ bị DB từ chối; báo sớm với nguyên nhân rõ ràng.
            raise EmbeddingError(
                f"Model {self._model_name} tạo vector {actual} chiều nhưng cấu hình là {self._dimensions}"
            )

    def _reject_texts_over_the_limit(self, model: Any, prefixed_texts: list[str]) -> None:
        limit = model.max_seq_length
        # Đếm token thật (gồm token đặc biệt) vì model cắt âm thầm phần vượt giới hạn.
        token_lengths = [len(ids) for ids in model.tokenizer(prefixed_texts)["input_ids"]]
        for index, length in enumerate(token_lengths):
            if length > limit:
                raise InputTooLongError(
                    f"Đoạn thứ {index + 1} dài {length} token, vượt giới hạn {limit} token của model; "
                    "hãy giảm kích thước chunk"
                )
