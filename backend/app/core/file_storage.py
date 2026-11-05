"""Lưu file gốc người dùng upload vào thư mục `settings.upload_dir`.

Tên file trên đĩa do server tạo (`<user_id>/<document_id><đuôi>`), không bao giờ lấy từ tên client gửi,
nên không có nguy cơ path traversal từ tên file.
"""

import os
import uuid
from pathlib import Path

from app.core.config import settings


def build_storage_path(user_id: uuid.UUID, document_id: uuid.UUID, extension: str) -> str:
    """Đường dẫn tương đối (dùng dấu `/`), lưu vào documents.storage_path."""
    return f"{user_id}/{document_id}{extension}"


def _resolve(relative_path: str) -> Path:
    base = Path(settings.upload_dir).resolve()
    target = (base / relative_path).resolve()
    if base != target and base not in target.parents:
        # Phòng thủ nhiều lớp: dù đường dẫn do server tạo, vẫn không bao giờ ghi ra ngoài thư mục upload.
        raise ValueError("Đường dẫn nằm ngoài thư mục upload")
    return target


def save_file(relative_path: str, content: bytes) -> None:
    target = _resolve(relative_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_name(target.name + ".part")
    try:
        temp.write_bytes(content)
        os.replace(temp, target)  # ghi nguyên tử: không để lại file dở dang dưới tên chính thức
    finally:
        temp.unlink(missing_ok=True)


def delete_file(relative_path: str) -> None:
    _resolve(relative_path).unlink(missing_ok=True)


def read_file(relative_path: str) -> bytes:
    return _resolve(relative_path).read_bytes()
