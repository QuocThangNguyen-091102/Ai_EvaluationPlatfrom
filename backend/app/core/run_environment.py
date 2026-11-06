"""Ảnh chụp môi trường chạy, lưu vào mỗi lượt đánh giá để tái lập và giải thích khác biệt giữa các lần chạy."""

import platform
from datetime import datetime, timezone
from importlib import metadata

_PACKAGES = ("fastapi", "sqlalchemy", "pgvector", "sentence-transformers", "transformers", "torch", "pypdf", "python-docx")


def package_versions() -> dict[str, str | None]:
    versions = {}
    for name in _PACKAGES:
        try:
            versions[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            versions[name] = None
    return versions


def snapshot(**extra) -> dict:
    return {
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "python": platform.python_version(),
        "packages": package_versions(),
        **extra,
    }
