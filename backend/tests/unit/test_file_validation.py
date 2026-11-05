import io
import zipfile

import pytest

from app.core.file_validation import (
    DOCX_CONTENT_TYPE,
    PDF_CONTENT_TYPE,
    TXT_CONTENT_TYPE,
    UnsupportedFileTypeError,
    detect_file_type,
    sanitize_display_name,
)

PDF_BYTES = b"%PDF-1.7\n%fake but starts like a pdf\n"


def make_docx(include_document_xml: bool = True) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        if include_document_xml:
            archive.writestr("word/document.xml", "<document/>")
    return buffer.getvalue()


def test_detects_pdf_docx_and_txt():
    assert detect_file_type("a.pdf", PDF_BYTES).content_type == PDF_CONTENT_TYPE
    assert detect_file_type("a.docx", make_docx()).content_type == DOCX_CONTENT_TYPE
    assert detect_file_type("a.txt", "Xin chào, đây là văn bản tiếng Việt".encode()).content_type == TXT_CONTENT_TYPE


def test_extension_is_case_insensitive():
    assert detect_file_type("BAO-CAO.PDF", PDF_BYTES).extension == ".pdf"


def test_txt_with_utf8_bom_is_accepted():
    assert detect_file_type("a.txt", b"\xef\xbb\xbf" + "nội dung".encode()).extension == ".txt"


@pytest.mark.parametrize("name", ["virus.exe", "ghi-chu.doc", "bang.xlsx", "khongduoi", "", None])
def test_other_extensions_are_rejected(name):
    with pytest.raises(UnsupportedFileTypeError):
        detect_file_type(name, PDF_BYTES)


def test_pdf_extension_with_non_pdf_content_is_rejected():
    with pytest.raises(UnsupportedFileTypeError):
        detect_file_type("fake.pdf", b"MZ\x90\x00 this is an executable")


def test_docx_extension_with_plain_zip_is_rejected():
    with pytest.raises(UnsupportedFileTypeError):
        detect_file_type("fake.docx", make_docx(include_document_xml=False))


def test_docx_extension_with_non_zip_content_is_rejected():
    with pytest.raises(UnsupportedFileTypeError):
        detect_file_type("fake.docx", b"PK this only pretends to be a zip")


def test_txt_with_binary_content_is_rejected():
    with pytest.raises(UnsupportedFileTypeError):
        detect_file_type("fake.txt", b"abc\x00\x01\x02def")


def test_txt_not_in_utf8_is_rejected_with_a_helpful_message():
    legacy_encoded = "Tiếng Việt".encode("utf-16")

    with pytest.raises(UnsupportedFileTypeError, match="UTF-8"):
        detect_file_type("legacy.txt", legacy_encoded)


def test_txt_in_windows_1258_is_rejected_with_the_utf8_message():
    # Windows-1258 là bảng mã tiếng Việt cũ; chữ "ê" là một byte 0xEA, không phải UTF-8 hợp lệ.
    legacy = "Viêt Nam".encode("cp1258")

    with pytest.raises(UnsupportedFileTypeError, match="UTF-8"):
        detect_file_type("cu.txt", legacy)


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("../../etc/passwd.txt", "passwd.txt"),
        ("C:\\Users\\a\\secret.pdf", "secret.pdf"),
        ("báo cáo quý 3.pdf", "báo cáo quý 3.pdf"),
        ("a\x00b\nc.txt", "abc.txt"),
        ("", "tai-lieu"),
        (None, "tai-lieu"),
    ],
)
def test_display_name_is_sanitized(raw, expected):
    assert sanitize_display_name(raw) == expected


def test_display_name_is_truncated():
    assert len(sanitize_display_name("x" * 1000 + ".pdf")) == 255
