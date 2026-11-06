"""Tạo một lần các thành phần nặng dùng chung cả tiến trình (model embedding, LLM client, bảng giá).

Mọi chỗ khác nhận chúng qua dependency injection, nên test thay được bằng bản giả.
"""

from functools import lru_cache

from ai_engine.embeddings.base_embedder import Embedder
from ai_engine.embeddings.local_embedder import LocalEmbedder
from ai_engine.generation.base_llm_client import LlmClient
from ai_engine.generation.cost_estimator import PriceTable, load_price_table
from ai_engine.generation.openai_compatible_client import OpenAICompatibleClient
from app.core.config import settings
from app.core.rag_defaults import config_dir, get_rag_defaults


@lru_cache
def get_embedder() -> Embedder:
    defaults = get_rag_defaults()
    if defaults.embedding_provider != "local":
        raise ValueError(f"Embedding provider chưa được hỗ trợ: {defaults.embedding_provider}")
    return LocalEmbedder(defaults.embedding_model, dimensions=defaults.embedding_dimensions)


@lru_cache
def get_llm_client() -> LlmClient | None:
    """None nghĩa là chưa cấu hình LLM: pipeline chạy chế độ không LLM (trả các đoạn liên quan nhất)."""
    if not settings.llm_base_url or not settings.llm_model:
        return None
    return OpenAICompatibleClient(
        base_url=settings.llm_base_url,
        model=settings.llm_model,
        api_key=settings.llm_api_key,
        provider_name=settings.llm_provider_name,
        timeout_seconds=settings.llm_timeout_seconds,
    )


@lru_cache
def get_price_table() -> PriceTable:
    return load_price_table(config_dir() / "models.yaml")
