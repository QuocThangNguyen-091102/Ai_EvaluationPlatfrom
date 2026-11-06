from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.core.providers import get_embedder
from app.core.rag_defaults import get_rag_defaults
from app.database.session import get_session, open_session
from app.models.user import User
from app.repositories.document_repository import DocumentRepository
from app.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService
from app.services.document_service import DocumentService
from app.services.ingestion_service import IngestionService

# auto_error=False để thiếu token vẫn đi qua bộ xử lý lỗi chuẩn của dự án (không dùng lỗi mặc định của FastAPI).
_bearer_scheme = HTTPBearer(auto_error=False)


def get_auth_service(session: Session = Depends(get_session)) -> AuthService:
    return AuthService(UserRepository(session))


def get_document_service(session: Session = Depends(get_session)) -> DocumentService:
    return DocumentService(DocumentRepository(session))


def get_ingestion_service() -> IngestionService:
    return IngestionService(session_factory=open_session, embedder_provider=get_embedder, defaults=get_rag_defaults())


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    auth_service: AuthService = Depends(get_auth_service),
) -> User:
    """Dependency cho mọi endpoint cần đăng nhập. Trả user hiện tại hoặc 401."""
    if credentials is None:
        raise AppError(401, "unauthorized", "Thiếu thông tin đăng nhập", headers={"WWW-Authenticate": "Bearer"})
    return auth_service.get_user_from_token(credentials.credentials)
