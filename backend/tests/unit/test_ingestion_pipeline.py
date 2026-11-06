import pytest

from ai_engine.ingestion.ingestion_pipeline import ingest, parse_content
from ai_engine.ingestion.parsed_document import ParsingError
from tests.fakes import HashEmbedder


def test_ingest_txt_produces_embedded_chunks_and_processing_config():
    embedder = HashEmbedder()
    text = " ".join(f"w{i}" for i in range(30))

    result = ingest(text.encode(), "text/plain", chunk_size=10, chunk_overlap=2, embedder=embedder)

    assert [item.chunk.index for item in result.chunks] == [0, 1, 2, 3]
    assert all(len(item.embedding) == 384 for item in result.chunks)
    assert embedder.passage_calls == [[item.chunk.content for item in result.chunks]]
    assert result.processing_config == {
        "chunk_size": 10,
        "chunk_overlap": 2,
        "chunk_unit": "words",
        "embedding_model": "test-hash-embedder",
    }


def test_unsupported_content_type_is_a_parsing_error():
    with pytest.raises(ParsingError):
        parse_content("image/png", b"\x89PNG")


def test_document_with_only_whitespace_is_a_parsing_error():
    with pytest.raises(ParsingError):
        ingest("   \n​  ".encode(), "text/plain", chunk_size=10, chunk_overlap=0, embedder=HashEmbedder())


def test_vector_count_mismatch_is_caught():
    class BrokenEmbedder(HashEmbedder):
        def embed_passages(self, texts):
            return []

    with pytest.raises(ParsingError):
        ingest(b"mot hai ba", "text/plain", chunk_size=10, chunk_overlap=0, embedder=BrokenEmbedder())
