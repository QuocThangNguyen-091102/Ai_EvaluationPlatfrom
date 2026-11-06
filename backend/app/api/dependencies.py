from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from ai_engine.pipeline.rag_pipeline import RagPipeline
from app.core.providers import get_embedder, get_rag_pipeline, llm_client_for_model
from app.core.rag_defaults import get_rag_defaults
from app.database.session import get_session, open_session
from app.models.user import User
from app.repositories.chat_repository import ChatRepository
from app.repositories.dataset_repository import DatasetRepository
from app.repositories.document_repository import DocumentRepository
from app.repositories.evaluation_repository import EvaluationRepository
from app.repositories.security_repository import SecurityRepository
from app.repositories.model_config_repository import ModelConfigRepository
from app.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService
from app.services.chat_service import ChatService
from app.services.dataset_service import DatasetService
from app.services.document_service import DocumentService
from app.services.evaluation_service import EvaluationRunService, EvaluationService
from app.services.security_service import SecurityRunService, SecurityService
from app.services.ingestion_service import IngestionService
from app.services.model_config_service import ModelConfigService

# auto_error=False để thiếu token vẫn đi qua bộ xử lý lỗi chuẩn của dự án (không dùng lỗi mặc định của FastAPI).
_bearer_scheme = HTTPBearer(auto_error=False)


def get_auth_service(session: Session = Depends(get_session)) -> AuthService:
    return AuthService(UserRepository(session))


def get_document_service(session: Session = Depends(get_session)) -> DocumentService:
    return DocumentService(DocumentRepository(session))


def get_ingestion_service() -> IngestionService:
    return IngestionService(session_factory=open_session, embedder_provider=get_embedder, defaults=get_rag_defaults())


def get_pipeline() -> RagPipeline:
    return get_rag_pipeline()


def get_model_config_service(session: Session = Depends(get_session)) -> ModelConfigService:
    return ModelConfigService(ModelConfigRepository(session), get_rag_defaults())


def get_chat_service(
    session: Session = Depends(get_session),
    pipeline: RagPipeline = Depends(get_pipeline),
) -> ChatService:
    return ChatService(ChatRepository(session), ModelConfigService(ModelConfigRepository(session), get_rag_defaults()), pipeline)


def get_dataset_service(session: Session = Depends(get_session)) -> DatasetService:
    return DatasetService(DatasetRepository(session))


def get_evaluation_service(session: Session = Depends(get_session)) -> EvaluationService:
    return EvaluationService(
        EvaluationRepository(session),
        DatasetRepository(session),
        ModelConfigService(ModelConfigRepository(session), get_rag_defaults()),
    )


def get_evaluation_run_service() -> EvaluationRunService:
    return EvaluationRunService(session_factory=open_session, pipeline_provider=get_pipeline, judge_client_for=llm_client_for_model)


def get_security_service(session: Session = Depends(get_session)) -> SecurityService:
    return SecurityService(SecurityRepository(session), ModelConfigService(ModelConfigRepository(session), get_rag_defaults()))


def get_security_run_service() -> SecurityRunService:
    return SecurityRunService(
        session_factory=open_session, pipeline_provider=get_pipeline, embedder_provider=get_embedder, judge_client_for=llm_client_for_model
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    auth_service: AuthService = Depends(get_auth_service),
) -> User:
    """Dependency cho mọi endpoint cần đăng nhập. Trả user hiện tại hoặc 401."""
    if credentials is None:
        raise AppError(401, "unauthorized", "Thiếu thông tin đăng nhập", headers={"WWW-Authenticate": "Bearer"})
    return auth_service.get_user_from_token(credentials.credentials)
