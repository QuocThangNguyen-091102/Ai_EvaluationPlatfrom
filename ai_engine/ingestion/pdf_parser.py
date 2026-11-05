import io

from pypdf import PdfReader

from ai_engine.ingestion.parsed_document import ParsedDocument, ParsedPage, ParsingError

# Chặn file PDF có số trang bất thường làm tốn tài nguyên khi xử lý.
DEFAULT_MAX_PAGES = 1000


def parse_pdf(content: bytes, *, max_pages: int = DEFAULT_MAX_PAGES) -> ParsedDocument:
    """Trích văn bản theo từng trang. Không có OCR: PDF dạng ảnh quét không có văn bản để trích."""
    try:
        reader = PdfReader(io.BytesIO(content))
        if reader.is_encrypted and not reader.decrypt(""):
            raise ParsingError("PDF được bảo vệ bằng mật khẩu")
        page_count = len(reader.pages)
    except ParsingError:
        raise
    except Exception:
        raise ParsingError("Không đọc được file PDF (file có thể bị hỏng)") from None

    if page_count > max_pages:
        raise ParsingError(f"PDF có quá nhiều trang (tối đa {max_pages})")

    pages: list[ParsedPage] = []
    for index in range(page_count):
        try:
            text = reader.pages[index].extract_text() or ""
        except Exception:
            # Không bỏ qua trang lỗi một cách im lặng: thiếu nội dung làm sai mọi kết quả phía sau.
            raise ParsingError(f"Không đọc được trang {index + 1} của PDF") from None
        text = text.strip()
        if text:
            pages.append(ParsedPage(text=text, page_number=index + 1))

    if not pages:
        raise ParsingError(
            "Không tìm thấy văn bản trong PDF (có thể là PDF dạng ảnh quét; hệ thống chưa hỗ trợ OCR)"
        )
    return ParsedDocument(pages=pages)
