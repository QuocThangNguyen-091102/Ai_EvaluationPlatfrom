"""Tạo một lần các thành phần nặng dùng chung cả tiến trình (model embedding, LLM client, bảng giá).

Mọi chỗ khác nhận chúng qua dependency injection, nên test thay được bằng bản giả.
"""

from functools import lru_cache

from ai_engine.embeddings.base_embedder import Embedder
from ai_engine.embeddings.local_embedder import LocalEmbedder
from ai_engine.generation.base_llm_client import LlmClient, LlmError
from ai_engine.generation.cost_estimator import PriceTable, load_price_table
from ai_engine.generation.openai_compatible_client import OpenAICompatibleClient
from ai_engine.pipeline.rag_config import RAGConfig
from ai_engine.pipeline.rag_pipeline import RagPipeline
from app.core.config import settings
from app.core.rag_defaults import config_dir, get_rag_defaults


@lru_cache
def get_embedder() -> Embedder:
    defaults = get_rag_defaults()
    if defaults.embedding_provider != "local":
        raise ValueError(f"Embedding provider chưa được hỗ trợ: {defaults.embedding_provider}")
    return LocalEmbedder(defaults.embedding_model, dimensions=defaults.embedding_dimensions)


class LlmNotConfiguredError(LlmError):
    """Cấu hình đòi một LLM mà máy chủ không kết nối (service đã kiểm tra trước, đây là lớp chặn cuối)."""


@lru_cache
def _client_for_model(model: str) -> LlmClient:
    return OpenAICompatibleClient(
        base_url=settings.llm_base_url,
        model=model,
        api_key=settings.llm_api_key,
        provider_name=settings.llm_provider_name,
        timeout_seconds=settings.llm_timeout_seconds,
    )


def llm_client_for(config: RAGConfig) -> LlmClient:
    """Client cho model trong cấu hình. Cùng một provider (cùng base_url, key) có thể chạy nhiều model để benchmark."""
    if not settings.llm_base_url or config.llm_provider != settings.llm_provider_name:
        raise LlmNotConfiguredError(f"Máy chủ không có LLM provider {config.llm_provider}")
    return _client_for_model(config.llm_model)


@lru_cache
def get_price_table() -> PriceTable:
    return load_price_table(config_dir() / "models.yaml")


@lru_cache
def get_rag_pipeline() -> RagPipeline:
    return RagPipeline(embedder=get_embedder(), llm_for=llm_client_for, price_table=get_price_table())
