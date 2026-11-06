from ai_engine.generation.prompt_templates import available_prompt_versions
from ai_engine.pipeline.rag_config import EXTRACTIVE_MODEL, EXTRACTIVE_PROVIDER, RAGConfig
from app.core.config import settings
from app.core.exceptions import AppError
from app.core.rag_defaults import RagDefaults
from app.models.model_config import ModelConfiguration
from app.models.user import User
from app.repositories.model_config_repository import DuplicateConfigurationNameError, ModelConfigRepository
from app.schemas.model_config import ModelConfigurationCreate, ServerCapabilities


def llm_configured() -> bool:
    return bool(settings.llm_base_url and settings.llm_model)


class ModelConfigService:
    """Tạo, đọc cấu hình RAG và kiểm tra chúng khớp với những gì máy chủ thật sự chạy được."""

    def __init__(self, configs: ModelConfigRepository, defaults: RagDefaults) -> None:
        self._configs = configs
        self._defaults = defaults

    def capabilities(self) -> ServerCapabilities:
        configured = llm_configured()
        return ServerCapabilities(
            llm_configured=configured,
            llm_provider=settings.llm_provider_name if configured else None,
            default_llm_model=settings.llm_model if configured else None,
            embedding_provider=self._defaults.embedding_provider,
            embedding_model=self._defaults.embedding_model,
            prompt_versions=available_prompt_versions(),
        )

    def create(self, user: User, payload: ModelConfigurationCreate) -> ModelConfiguration:
        self._check_llm(payload.llm_provider, payload.llm_model)
        prompt_version = payload.prompt_version or self._defaults.prompt_version
        if prompt_version not in available_prompt_versions():
            raise AppError(422, "validation_error", f"Không có prompt phiên bản {prompt_version}")
        embedding_provider = payload.embedding_provider or self._defaults.embedding_provider
        embedding_model = payload.embedding_model or self._defaults.embedding_model
        if (embedding_provider, embedding_model) != (self._defaults.embedding_provider, self._defaults.embedding_model):
            raise AppError(
                422,
                "validation_error",
                f"Máy chủ chỉ dùng embedding {self._defaults.embedding_model}; đổi model embedding cần embed lại toàn bộ tài liệu",
            )
        chunk_size = payload.chunk_size or self._defaults.chunk_size
        chunk_overlap = self._defaults.chunk_overlap if payload.chunk_overlap is None else payload.chunk_overlap
        if chunk_overlap >= chunk_size:
            raise AppError(422, "validation_error", "chunk_overlap phải nhỏ hơn chunk_size")
        config = ModelConfiguration(
            user_id=user.id,
            name=payload.name.strip(),
            llm_provider=payload.llm_provider,
            llm_model=payload.llm_model,
            embedding_provider=embedding_provider,
            embedding_model=embedding_model,
            prompt_version=prompt_version,
            top_k=payload.top_k or self._defaults.top_k,
            temperature=self._defaults.temperature if payload.temperature is None else payload.temperature,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
        try:
            self._configs.add(config)
        except DuplicateConfigurationNameError:
            raise AppError(409, "conflict", "Bạn đã có cấu hình cùng tên") from None
        self._configs.commit()
        return config

    def get(self, user: User, config_id) -> ModelConfiguration:
        config = self._configs.get_for_user(user.id, config_id)
        if config is None:
            raise AppError(404, "not_found", "Không tìm thấy cấu hình")
        return config

    def list(self, user: User, *, limit: int, offset: int):
        return self._configs.list_for_user(user.id, limit=limit, offset=offset)

    def resolve_for_use(self, user: User, config_id) -> ModelConfiguration:
        """Cấu hình được chọn (phải thuộc user và chạy được trên máy chủ), hoặc cấu hình mặc định."""
        config = self.get(user, config_id) if config_id is not None else self.default_for(user)
        self._check_llm(config.llm_provider, config.llm_model)
        return config

    def default_for(self, user: User) -> ModelConfiguration:
        if llm_configured():
            provider, model = settings.llm_provider_name, settings.llm_model
        else:
            provider, model = EXTRACTIVE_PROVIDER, EXTRACTIVE_MODEL
        name = f"Mặc định ({provider}/{model})"[:100]
        existing = self._configs.get_by_name(user.id, name)
        if existing is not None:
            return existing
        return self.create(user, ModelConfigurationCreate(name=name, llm_provider=provider, llm_model=model))

    @staticmethod
    def to_rag_config(config: ModelConfiguration) -> RAGConfig:
        return RAGConfig(
            top_k=config.top_k,
            temperature=config.temperature,
            prompt_version=config.prompt_version,
            llm_provider=config.llm_provider,
            llm_model=config.llm_model,
        )

    @staticmethod
    def _check_llm(provider: str, model: str) -> None:
        if provider == EXTRACTIVE_PROVIDER:
            if model != EXTRACTIVE_MODEL:
                raise AppError(422, "validation_error", f"Chế độ không LLM chỉ có model {EXTRACTIVE_MODEL}")
            return
        if not llm_configured():
            raise AppError(
                422,
                "validation_error",
                "Máy chủ chưa cấu hình LLM; chỉ dùng được chế độ không LLM (extractive). Xem LLM_BASE_URL trong .env",
            )
        if provider != settings.llm_provider_name:
            raise AppError(422, "validation_error", f"Máy chủ chỉ kết nối LLM provider {settings.llm_provider_name}")
