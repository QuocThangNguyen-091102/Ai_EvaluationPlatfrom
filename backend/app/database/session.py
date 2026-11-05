from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session

from app.core.config import settings


@lru_cache
def get_engine() -> Engine:
    """Tạo engine ở lần dùng đầu (không tạo lúc import) để test không cần DB vẫn import được app."""
    return create_engine(settings.database_url, pool_pre_ping=True)


def get_session() -> Iterator[Session]:
    """Dependency của FastAPI: một session cho mỗi request, tự đóng khi xong."""
    with Session(get_engine()) as session:
        yield session
