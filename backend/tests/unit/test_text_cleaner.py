import unicodedata

import pytest

from ai_engine.ingestion.parsed_document import ParsedDocument, ParsedPage, ParsingError
from ai_engine.ingestion.text_cleaner import clean_document, clean_text


def test_vietnamese_text_is_normalized_to_nfc():
    decomposed = unicodedata.normalize("NFD", "Hồ sơ xin cấp giấy phép")
    assert decomposed != "Hồ sơ xin cấp giấy phép"

    assert clean_text(decomposed) == "Hồ sơ xin cấp giấy phép"


def test_runs_of_spaces_tabs_and_nbsp_collapse_to_one_space():
    assert clean_text("a  \t b  c") == "a b c"


def test_invisible_characters_are_removed():
    assert clean_text("ab​cd﻿ef­gh") == "abcdefgh"


def test_control_characters_are_removed_but_newlines_stay():
    assert clean_text("dong1\x00\x07\ndong2") == "dong1\ndong2"


def test_line_endings_are_normalized_and_lines_are_trimmed():
    assert clean_text("  dong 1  \r\n  dong 2  \r dong 3") == "dong 1\ndong 2\ndong 3"


def test_many_blank_lines_collapse_to_one_paragraph_break():
    assert clean_text("đoạn 1\n\n\n\n\nđoạn 2") == "đoạn 1\n\nđoạn 2"


def test_single_line_breaks_are_kept_not_joined():
    # DOCX và bảng dùng xuống dòng làm ranh giới thật; không nối để khỏi mất cấu trúc.
    assert clean_text("Tiêu đề\nNội dung\nBảng | 1 | 2") == "Tiêu đề\nNội dung\nBảng | 1 | 2"


def test_hyphen_at_line_end_is_left_alone():
    assert clean_text("xuyên-\nsuốt") == "xuyên-\nsuốt"


def test_cleaning_is_idempotent():
    once = clean_text("  Ví   dụ ​ với \n\n\n\n nhiều   dòng\t ")
    assert clean_text(once) == once


def test_clean_document_keeps_page_numbers_and_drops_blank_pages():
    document = ParsedDocument(
        pages=[
            ParsedPage(text="Trang  một", page_number=1),
            ParsedPage(text=" \n​ ", page_number=2),
            ParsedPage(text="Trang ba", page_number=3),
        ]
    )

    cleaned = clean_document(document)

    assert [(p.text, p.page_number) for p in cleaned.pages] == [("Trang một", 1), ("Trang ba", 3)]


def test_clean_document_with_nothing_left_is_an_error():
    with pytest.raises(ParsingError):
        clean_document(ParsedDocument(pages=[ParsedPage(text="​ \n ", page_number=None)]))
