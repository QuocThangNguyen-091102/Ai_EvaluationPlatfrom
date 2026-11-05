from ai_engine.ingestion.parsed_document import ParsedDocument, ParsedPage, ParsingError


def parse_txt(content: bytes) -> ParsedDocument:
    """Đọc file TXT mã hóa UTF-8 (có hoặc không có BOM)."""
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise ParsingError("File TXT phải được lưu với mã hóa UTF-8") from None

    text = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not text:
        raise ParsingError("File không có nội dung văn bản")
    return ParsedDocument(pages=[ParsedPage(text=text, page_number=None)])
