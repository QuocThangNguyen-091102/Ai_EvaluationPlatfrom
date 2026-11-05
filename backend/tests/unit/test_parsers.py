import io
import zipfile
from pathlib import Path

import pytest
from docx import Document
from pypdf import PdfWriter

from ai_engine.ingestion.docx_parser import parse_docx
from ai_engine.ingestion.parsed_document import ParsingError
from ai_engine.ingestion.pdf_parser import parse_pdf
from ai_engine.ingestion.txt_parser import parse_txt

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


# ---------------------------------------------------------------- TXT
def test_txt_vietnamese_text_is_read_intact():
    parsed = parse_txt("Hồ sơ phải nộp trong vòng 30 ngày.".encode("utf-8"))

    assert parsed.text == "Hồ sơ phải nộp trong vòng 30 ngày."
    assert parsed.pages[0].page_number is None


def test_txt_bom_is_removed_and_line_endings_are_normalized():
    parsed = parse_txt(b"\xef\xbb\xbfdong 1\r\ndong 2\rdong 3\n")

    assert parsed.text == "dong 1\ndong 2\ndong 3"


@pytest.mark.parametrize("content", [b"", b"   \n\t  \r\n"])
def test_txt_without_text_is_an_error(content):
    with pytest.raises(ParsingError, match="không có nội dung"):
        parse_txt(content)


def test_txt_not_in_utf8_is_an_error():
    with pytest.raises(ParsingError, match="UTF-8"):
        parse_txt("Viêt Nam".encode("cp1258"))


# ---------------------------------------------------------------- DOCX
def _docx_bytes(build) -> bytes:
    document = Document()
    build(document)
    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def test_docx_paragraphs_and_tables_are_read_in_document_order():
    def build(document):
        document.add_paragraph("Quy định nộp hồ sơ")
        table = document.add_table(rows=2, cols=2)
        table.cell(0, 0).text = "Loại hồ sơ"
        table.cell(0, 1).text = "Thời hạn"
        table.cell(1, 0).text = "Giấy phép"
        table.cell(1, 1).text = "30 ngày"
        document.add_paragraph("Hết quy định.")

    parsed = parse_docx(_docx_bytes(build))

    assert parsed.text.split("\n") == [
        "Quy định nộp hồ sơ",
        "Loại hồ sơ | Thời hạn",
        "Giấy phép | 30 ngày",
        "Hết quy định.",
    ]
    assert parsed.pages[0].page_number is None


def test_docx_merged_cells_are_not_repeated():
    def build(document):
        table = document.add_table(rows=1, cols=3)
        merged = table.cell(0, 0).merge(table.cell(0, 1))
        merged.text = "Ô gộp"
        table.cell(0, 2).text = "Ô thường"

    assert parse_docx(_docx_bytes(build)).text == "Ô gộp | Ô thường"


def test_docx_without_text_is_an_error():
    with pytest.raises(ParsingError, match="không có nội dung"):
        parse_docx(_docx_bytes(lambda document: document.add_paragraph("   ")))


def test_corrupt_docx_is_a_parsing_error_not_a_crash():
    broken = io.BytesIO()
    with zipfile.ZipFile(broken, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr("word/document.xml", "đây không phải XML hợp lệ <<<")

    with pytest.raises(ParsingError, match="DOCX"):
        parse_docx(broken.getvalue())


def test_non_zip_content_is_a_parsing_error():
    with pytest.raises(ParsingError, match="DOCX"):
        parse_docx(b"PK khong phai zip that")


def test_docx_with_huge_uncompressed_size_is_rejected_before_parsing():
    bomb = io.BytesIO()
    with zipfile.ZipFile(bomb, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr("word/document.xml", "a" * (2 * 1024 * 1024))  # nén rất nhỏ, giải nén 2 MB

    with pytest.raises(ParsingError, match="quá lớn"):
        parse_docx(bomb.getvalue(), max_uncompressed_bytes=1024 * 1024)


# ---------------------------------------------------------------- PDF
def test_pdf_with_vietnamese_text_is_read_per_page_with_page_numbers():
    parsed = parse_pdf((FIXTURES / "vi_two_pages.pdf").read_bytes())

    assert [page.page_number for page in parsed.pages] == [1, 2]
    # PDF xuống dòng theo bố cục trang (một câu bị ngắt thành hai dòng), nên so sánh sau khi gộp khoảng trắng.
    # Việc nối lại các dòng bị ngắt là của bước làm sạch văn bản (text_cleaner).
    first_page = " ".join(parsed.pages[0].text.split())
    assert "Quy định nộp hồ sơ" in first_page
    assert "30 ngày kể từ ngày nhận được thông báo chấp thuận" in first_page
    assert "Phí và lệ phí" in parsed.pages[1].text


def _pdf_bytes(configure) -> bytes:
    writer = PdfWriter()
    configure(writer)
    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def test_pdf_without_text_such_as_scanned_images_gets_a_clear_error():
    blank = _pdf_bytes(lambda writer: writer.add_blank_page(width=200, height=200))

    with pytest.raises(ParsingError, match="ảnh quét"):
        parse_pdf(blank)


def test_password_protected_pdf_is_rejected_with_a_clear_error():
    def configure(writer):
        writer.add_blank_page(width=200, height=200)
        writer.encrypt("mat-khau-bi-mat")

    with pytest.raises(ParsingError, match="mật khẩu"):
        parse_pdf(_pdf_bytes(configure))


def test_corrupt_pdf_is_a_parsing_error_not_a_crash():
    with pytest.raises(ParsingError, match="PDF"):
        parse_pdf(b"%PDF-1.7\nday khong phai pdf hop le, hong nang\n%%EOF")


def test_pdf_with_too_many_pages_is_rejected():
    many = _pdf_bytes(lambda writer: [writer.add_blank_page(width=10, height=10) for _ in range(5)])

    with pytest.raises(ParsingError, match="quá nhiều trang"):
        parse_pdf(many, max_pages=3)


def test_error_messages_never_contain_file_content():
    secret = "NOI-DUNG-BI-MAT-12345"
    corrupt = f"%PDF-1.7\n{secret}\n".encode()

    with pytest.raises(ParsingError) as error:
        parse_pdf(corrupt)

    assert secret not in str(error.value)
