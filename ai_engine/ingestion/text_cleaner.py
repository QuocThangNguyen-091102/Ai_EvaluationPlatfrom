"""Chuẩn hóa văn bản sau khi parse, trước khi chia chunk.

Nguyên tắc: chỉ làm những thay đổi không mất thông tin. Không nối các dòng bị ngắt (DOCX dùng xuống dòng làm
ranh giới đoạn thật; nối bừa sẽ làm mất cấu trúc) và không tự bỏ gạch nối cuối dòng (không phân biệt được
gạch nối ngắt từ với gạch nối thật).
"""

import re
import unicodedata

from ai_engine.ingestion.parsed_document import ParsedDocument, ParsedPage, ParsingError

# Ký tự không hiển thị: zero-width space/joiner, word joiner, BOM, soft hyphen.
_INVISIBLE = dict.fromkeys(map(ord, "​‌‍⁠﻿­"), None)
# Ký tự điều khiển (giữ lại \t và \n để xử lý riêng ở dưới).
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
# Mọi khoảng trắng trừ xuống dòng (gồm tab, NBSP, khoảng trắng Unicode khác).
_INLINE_WHITESPACE = re.compile(r"[^\S\n]+")
_BLANK_LINE_RUN = re.compile(r"\n{3,}")


def clean_text(text: str) -> str:
    # NFC: cùng một chữ có dấu luôn có cùng một chuỗi mã, nếu không "ế" dạng tổ hợp và dạng tách rời sẽ khác nhau
    # khi so khớp và khi embedding.
    text = unicodedata.normalize("NFC", text)
    text = text.translate(_INVISIBLE)
    text = _CONTROL.sub("", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _INLINE_WHITESPACE.sub(" ", text)
    text = "\n".join(line.strip() for line in text.split("\n"))
    text = _BLANK_LINE_RUN.sub("\n\n", text)
    return text.strip()


def clean_document(document: ParsedDocument) -> ParsedDocument:
    """Làm sạch từng trang và bỏ các trang chỉ còn khoảng trắng."""
    pages = []
    for page in document.pages:
        cleaned = clean_text(page.text)
        if cleaned:
            pages.append(ParsedPage(text=cleaned, page_number=page.page_number))
    if not pages:
        raise ParsingError("File không có nội dung văn bản")
    return ParsedDocument(pages=pages)
