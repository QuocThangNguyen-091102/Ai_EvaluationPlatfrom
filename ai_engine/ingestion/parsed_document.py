"""Kiểu dữ liệu chung cho kết quả đọc file, dùng bởi cả ba parser."""

from dataclasses import dataclass


class ParsingError(Exception):
    """Không đọc được file. Thông điệp an toàn để hiển thị cho người dùng (không chứa nội dung file)."""


@dataclass(frozen=True)
class ParsedPage:
    text: str
    # Số trang bắt đầu từ 1; None với định dạng không có khái niệm trang (TXT, DOCX).
    page_number: int | None


@dataclass(frozen=True)
class ParsedDocument:
    pages: list[ParsedPage]

    @property
    def text(self) -> str:
        return "\n\n".join(page.text for page in self.pages)
