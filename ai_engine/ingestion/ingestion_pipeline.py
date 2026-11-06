"""Pipeline ingestion thuần: bytes của file -> văn bản -> làm sạch -> chunk -> vector.

Không biết gì về database hay HTTP; backend gọi hàm này rồi tự lưu kết quả. Lỗi do file thì ném `ParsingError`,
lỗi do embedding thì ném `EmbeddingError`; cả hai có thông điệp an toàn để hiển thị cho người dùng.
"""

from dataclasses import dataclass

from ai_engine.chunking.fixed_size_chunker import Chunk, chunk_document
from ai_engine.embeddings.base_embedder import Embedder
from ai_engine.ingestion.docx_parser import parse_docx
from ai_engine.ingestion.parsed_document import ParsedDocument, ParsingError
from ai_engine.ingestion.pdf_parser import parse_pdf
from ai_engine.ingestion.text_cleaner import clean_document
from ai_engine.ingestion.txt_parser import parse_txt

_PARSERS = {
    "application/pdf": parse_pdf,
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": parse_docx,
    "text/plain": parse_txt,
}


@dataclass(frozen=True)
class EmbeddedChunk:
    chunk: Chunk
    embedding: list[float]


@dataclass(frozen=True)
class IngestionResult:
    chunks: list[EmbeddedChunk]
    embedding_model: str
    chunk_size: int
    chunk_overlap: int

    @property
    def processing_config(self) -> dict:
        """Ghi vào documents.processing_config để biết tài liệu được xử lý bằng cấu hình nào."""
        return {
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap,
            "chunk_unit": "words",
            "embedding_model": self.embedding_model,
        }


def parse_content(content_type: str, content: bytes) -> ParsedDocument:
    try:
        parser = _PARSERS[content_type]
    except KeyError:
        raise ParsingError("Loại file không được hỗ trợ") from None
    return parser(content)


def ingest(content: bytes, content_type: str, *, chunk_size: int, chunk_overlap: int, embedder: Embedder) -> IngestionResult:
    document = clean_document(parse_content(content_type, content))
    chunks = chunk_document(document, chunk_size=chunk_size, overlap=chunk_overlap)
    if not chunks:
        raise ParsingError("File không có nội dung văn bản")
    vectors = embedder.embed_passages([chunk.content for chunk in chunks])
    if len(vectors) != len(chunks):
        raise ParsingError("Số vector không khớp số đoạn văn bản")
    return IngestionResult(
        chunks=[EmbeddedChunk(chunk=chunk, embedding=vector) for chunk, vector in zip(chunks, vectors)],
        embedding_model=embedder.model_name,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
