"""Nhận diện loại file upload bằng NỘI DUNG, không tin tên file hay Content-Type do client gửi.

Chỉ nhận PDF, DOCX và TXT (UTF-8). Hàm ở đây không giải nén hay phân tích sâu nội dung: việc đọc
văn bản nằm ở ai_engine/ingestion (M3-T04).
"""

import io
import zipfile
from dataclasses import dataclass
from pathlib import PurePosixPath, PureWindowsPath

PDF_CONTENT_TYPE = "application/pdf"
DOCX_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
TXT_CONTENT_TYPE = "text/plain"

_ALLOWED = {
    ".pdf": PDF_CONTENT_TYPE,
    ".docx": DOCX_CONTENT_TYPE,
    ".txt": TXT_CONTENT_TYPE,
}
_DISPLAY_NAME_MAX_LENGTH = 255


class UnsupportedFileTypeError(Exception):
    """File không phải PDF, DOCX hoặc TXT hợp lệ. Thông điệp dành cho người dùng."""


@dataclass(frozen=True)
class DetectedFile:
    content_type: str
    extension: str


def sanitize_display_name(filename: str | None) -> str:
    """Tên chỉ để hiển thị: bỏ thành phần đường dẫn, ký tự điều khiển, cắt độ dài. Không dùng làm đường dẫn file."""
    name = filename or ""
    name = PureWindowsPath(PurePosixPath(name).name).name  # xử lý cả "/" lẫn "\"
    name = "".join(ch for ch in name if ch.isprintable()).strip()
    return name[:_DISPLAY_NAME_MAX_LENGTH] or "tai-lieu"


def detect_file_type(filename: str | None, content: bytes) -> DetectedFile:
    extension = PurePosixPath(sanitize_display_name(filename)).suffix.lower()
    if extension not in _ALLOWED:
        raise UnsupportedFileTypeError("Chỉ chấp nhận file PDF, DOCX hoặc TXT")

    if extension == ".pdf":
        if not content.startswith(b"%PDF-"):
            raise UnsupportedFileTypeError("Nội dung không phải file PDF hợp lệ")
    elif extension == ".docx":
        if not _looks_like_docx(content):
            raise UnsupportedFileTypeError("Nội dung không phải file DOCX hợp lệ")
    else:
        _require_utf8_text(content)

    return DetectedFile(content_type=_ALLOWED[extension], extension=extension)


def _looks_like_docx(content: bytes) -> bool:
    if not content.startswith(b"PK"):
        return False
    try:
        # Chỉ đọc danh sách tên trong zip, không giải nén nội dung.
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            names = set(archive.namelist())
    except zipfile.BadZipFile:
        return False
    return "[Content_Types].xml" in names and "word/document.xml" in names


_NOT_UTF8_MESSAGE = "File TXT phải được lưu với mã hóa UTF-8"


def _require_utf8_text(content: bytes) -> None:
    # File "Unicode" của Notepad là UTF-16 và chứa byte 0; báo đúng nguyên nhân thay vì gọi là nhị phân.
    if content.startswith((b"\xff\xfe", b"\xfe\xff")):
        raise UnsupportedFileTypeError(_NOT_UTF8_MESSAGE)
    if b"\x00" in content:
        raise UnsupportedFileTypeError("File TXT chứa dữ liệu nhị phân")
    try:
        content.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise UnsupportedFileTypeError(_NOT_UTF8_MESSAGE) from None
