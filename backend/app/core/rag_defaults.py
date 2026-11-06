"""Đọc giá trị mặc định của RAG từ `configs/rag_default.yaml`."""

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml

from app.core.config import settings


@dataclass(frozen=True)
class RagDefaults:
    embedding_provider: str
    embedding_model: str
    embedding_dimensions: int
    chunk_size: int
    chunk_overlap: int
    top_k: int
    prompt_version: str
    temperature: float


def config_dir() -> Path:
    """Thư mục `configs/`: đặt bằng CONFIG_DIR, nếu không thì tìm cạnh mã nguồn (máy host hoặc container)."""
    if settings.config_dir:
        return Path(settings.config_dir)
    here = Path(__file__).resolve()
    for candidate in (here.parents[3] / "configs", here.parents[2] / "configs"):
        if candidate.is_dir():
            return candidate
    raise FileNotFoundError("Không tìm thấy thư mục configs; đặt biến môi trường CONFIG_DIR")


@lru_cache
def get_rag_defaults() -> RagDefaults:
    data = yaml.safe_load((config_dir() / "rag_default.yaml").read_text(encoding="utf-8"))
    defaults = RagDefaults(
        embedding_provider=str(data["embedding"]["provider"]),
        embedding_model=str(data["embedding"]["model"]),
        embedding_dimensions=int(data["embedding"]["dimensions"]),
        chunk_size=int(data["chunking"]["chunk_size"]),
        chunk_overlap=int(data["chunking"]["chunk_overlap"]),
        top_k=int(data["retrieval"]["top_k"]),
        prompt_version=str(data["generation"]["prompt_version"]),
        temperature=float(data["generation"]["temperature"]),
    )
    if not 0 <= defaults.chunk_overlap < defaults.chunk_size:
        raise ValueError("rag_default.yaml: chunk_overlap phải từ 0 đến nhỏ hơn chunk_size")
    if defaults.top_k < 1:
        raise ValueError("rag_default.yaml: top_k phải ít nhất là 1")
    return defaults
