from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Lớp cơ sở của mọi model ORM. Alembic đọc `Base.metadata` để biết schema."""
