import io
import zipfile

from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph

from ai_engine.ingestion.parsed_document import ParsedDocument, ParsedPage, ParsingError

# Tổng dung lượng sau giải nén tối đa (chặn "zip bomb": file nhỏ nhưng giải nén ra rất lớn).
DEFAULT_MAX_UNCOMPRESSED_BYTES = 100 * 1024 * 1024


def parse_docx(content: bytes, *, max_uncompressed_bytes: int = DEFAULT_MAX_UNCOMPRESSED_BYTES) -> ParsedDocument:
    """Trích văn bản của thân tài liệu (đoạn văn và bảng, đúng thứ tự xuất hiện).

    Giới hạn đã biết: không đọc header, footer, chú thích cuối trang, hộp văn bản và bảng lồng nhau.
    DOCX không có khái niệm trang cố định nên trả về một "trang" duy nhất với page_number None.
    """
    _reject_oversized_archive(content, max_uncompressed_bytes)

    try:
        document = Document(io.BytesIO(content))
        blocks: list[str] = []
        for item in document.iter_inner_content():
            if isinstance(item, Paragraph):
                blocks.append(item.text)
            elif isinstance(item, Table):
                blocks.extend(_table_rows(item))
    except Exception:
        raise ParsingError("Không đọc được file DOCX (file có thể bị hỏng)") from None

    text = "\n".join(block.strip() for block in blocks if block.strip())
    if not text:
        raise ParsingError("File không có nội dung văn bản")
    return ParsedDocument(pages=[ParsedPage(text=text, page_number=None)])


def _reject_oversized_archive(content: bytes, limit: int) -> None:
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            total = sum(info.file_size for info in archive.infolist())
    except zipfile.BadZipFile:
        raise ParsingError("Không đọc được file DOCX (file có thể bị hỏng)") from None
    if total > limit:
        raise ParsingError("File DOCX có dung lượng giải nén quá lớn")


def _table_rows(table: Table) -> list[str]:
    rows = []
    for row in table.rows:
        cells: list[str] = []
        previous = None
        for cell in row.cells:
            # Ô gộp được python-docx trả về lặp lại nhiều lần; chỉ lấy một lần.
            if cell._tc is previous:
                continue
            previous = cell._tc
            cells.append(cell.text.strip())
        rows.append(" | ".join(cells))
    return rows
