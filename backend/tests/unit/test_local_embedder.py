import os

import numpy as np
import pytest

from ai_engine.embeddings.base_embedder import EmbeddingError, InputTooLongError
from ai_engine.embeddings.local_embedder import PASSAGE_PREFIX, QUERY_PREFIX, LocalEmbedder


class FakeModel:
    """Thay cho SentenceTransformer: ghi lại đầu vào và trả vector cố định, không cần tải model thật."""

    max_seq_length = 20

    def __init__(self, dimensions: int = 384):
        self.dimensions = dimensions
        self.encoded_batches: list[list[str]] = []
        self.encode_kwargs: dict = {}

    def get_embedding_dimension(self) -> int:
        return self.dimensions

    def tokenizer(self, texts):
        # Mỗi từ là một token, cộng 2 token đặc biệt đầu và cuối như tokenizer thật.
        return {"input_ids": [list(range(len(text.split()) + 2)) for text in texts]}

    def encode(self, texts, **kwargs):
        self.encoded_batches.append(list(texts))
        self.encode_kwargs = kwargs
        return np.array([[0.5] * self.dimensions for _ in texts], dtype=np.float32)


def _embedder(model: FakeModel | None = None, **kwargs):
    model = model or FakeModel()
    calls = []

    def loader(name, device):
        calls.append((name, device))
        return model

    return LocalEmbedder(model_loader=loader, **kwargs), model, calls


def test_passages_get_the_passage_prefix_and_queries_get_the_query_prefix():
    embedder, model, _ = _embedder()

    embedder.embed_passages(["đoạn một", "đoạn hai"])
    embedder.embed_query("câu hỏi")

    assert model.encoded_batches == [
        [PASSAGE_PREFIX + "đoạn một", PASSAGE_PREFIX + "đoạn hai"],
        [QUERY_PREFIX + "câu hỏi"],
    ]
    assert PASSAGE_PREFIX == "passage: " and QUERY_PREFIX == "query: "


def test_vectors_are_plain_float_lists_with_the_configured_dimensions():
    embedder, _, _ = _embedder()

    vectors = embedder.embed_passages(["a", "b", "c"])

    assert len(vectors) == 3
    assert all(len(vector) == embedder.dimensions == 384 for vector in vectors)
    assert all(type(value) is float for vector in vectors for value in vector)


def test_vectors_are_requested_normalized_and_without_progress_bar():
    embedder, model, _ = _embedder(batch_size=7)

    embedder.embed_query("x")

    assert model.encode_kwargs["normalize_embeddings"] is True
    assert model.encode_kwargs["batch_size"] == 7
    assert model.encode_kwargs["show_progress_bar"] is False


def test_model_is_loaded_lazily_and_only_once():
    embedder, _, calls = _embedder()
    assert calls == []

    embedder.embed_query("một")
    embedder.embed_passages(["hai"])
    embedder.embed_query("ba")

    assert calls == [("intfloat/multilingual-e5-small", "cpu")]


def test_empty_input_returns_empty_list_without_loading_the_model():
    embedder, _, calls = _embedder()

    assert embedder.embed_passages([]) == []
    assert calls == []


def test_text_over_the_token_limit_is_rejected_and_nothing_is_encoded():
    embedder, model, _ = _embedder()
    too_long = " ".join(["từ"] * 30)

    with pytest.raises(InputTooLongError, match="Đoạn thứ 2"):
        embedder.embed_passages(["ngắn thôi", too_long])

    assert model.encoded_batches == []


def test_text_exactly_at_the_limit_is_accepted():
    embedder, model, _ = _embedder()
    # Tiền tố "passage:" là 1 từ + 2 token đặc biệt: 17 từ thường + 1 = 18 từ => 20 token = đúng giới hạn.
    at_limit = " ".join(["từ"] * 17)

    embedder.embed_passages([at_limit])

    assert len(model.encoded_batches) == 1


def test_error_message_never_contains_the_text():
    embedder, _, _ = _embedder()
    secret = "NOI-DUNG-BI-MAT " * 30

    with pytest.raises(InputTooLongError) as error:
        embedder.embed_passages([secret])

    assert "NOI-DUNG-BI-MAT" not in str(error.value)


def test_model_with_unexpected_dimensions_is_refused_with_a_clear_message():
    embedder, _, _ = _embedder(FakeModel(dimensions=768))

    with pytest.raises(EmbeddingError, match="768 chiều nhưng cấu hình là 384"):
        embedder.embed_query("x")


def test_failure_to_load_the_model_becomes_an_embedding_error():
    def broken_loader(name, device):
        raise OSError("không có mạng")

    embedder = LocalEmbedder(model_loader=broken_loader)

    with pytest.raises(EmbeddingError, match="Không nạp được model"):
        embedder.embed_query("x")


def test_failure_while_encoding_becomes_an_embedding_error_without_internal_detail():
    model = FakeModel()

    def broken_encode(texts, **kwargs):
        raise RuntimeError("chi tiết nội bộ không nên lộ")

    model.encode = broken_encode
    embedder, _, _ = _embedder(model)

    with pytest.raises(EmbeddingError) as error:
        embedder.embed_query("x")

    assert "chi tiết nội bộ" not in str(error.value)


def test_exposes_model_name_and_dimensions():
    embedder = LocalEmbedder(model_loader=lambda *_: FakeModel())

    assert embedder.model_name == "intfloat/multilingual-e5-small"
    assert embedder.dimensions == 384


# ------------------------------------------------------------------------------------------------------------
# Test với model thật: chậm (lần đầu phải tải khoảng vài trăm MB). Chỉ chạy khi đặt RUN_MODEL_TESTS=1.
requires_real_model = pytest.mark.skipif(
    os.getenv("RUN_MODEL_TESTS") != "1", reason="Đặt RUN_MODEL_TESTS=1 để chạy test với model embedding thật"
)


@pytest.fixture(scope="module")
def real_embedder():
    return LocalEmbedder()


@requires_real_model
def test_real_model_produces_vectors_with_the_dimension_the_database_expects(real_embedder):
    from app.models.document_chunk import EMBEDDING_DIMENSIONS

    vectors = real_embedder.embed_passages(["Hồ sơ phải nộp trong vòng 30 ngày."])

    assert len(vectors[0]) == EMBEDDING_DIMENSIONS == real_embedder.dimensions == 384


@requires_real_model
def test_real_model_ranks_a_relevant_vietnamese_passage_above_an_irrelevant_one(real_embedder):
    query = real_embedder.embed_query("Thời hạn nộp hồ sơ xin cấp giấy phép là bao lâu?")
    relevant, irrelevant = real_embedder.embed_passages(
        [
            "Hồ sơ xin cấp giấy phép phải được nộp trong vòng 30 ngày kể từ ngày nhận được thông báo chấp thuận.",
            "Món phở bò truyền thống được nấu từ xương ống hầm nhiều giờ cùng quế, hồi và gừng nướng.",
        ]
    )

    assert np.dot(query, relevant) > np.dot(query, irrelevant)


@requires_real_model
def test_real_model_vectors_are_normalized_and_deterministic(real_embedder):
    first = real_embedder.embed_query("kiểm tra tính ổn định")
    second = real_embedder.embed_query("kiểm tra tính ổn định")

    assert np.linalg.norm(first) == pytest.approx(1.0, abs=1e-4)
    assert first == pytest.approx(second, abs=1e-6)


@requires_real_model
def test_real_model_treats_query_and_passage_prefixes_differently(real_embedder):
    as_query = real_embedder.embed_query("giấy phép")
    as_passage = real_embedder.embed_passages(["giấy phép"])[0]

    assert np.dot(as_query, as_passage) < 0.9999


@requires_real_model
def test_real_model_rejects_text_that_would_be_silently_truncated(real_embedder):
    with pytest.raises(InputTooLongError):
        real_embedder.embed_passages(["Quy định về nộp hồ sơ xin cấp giấy phép. " * 120])
