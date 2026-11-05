import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, UniqueConstraint, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class User(Base):
    """Tài khoản đăng nhập, chủ sở hữu mọi dữ liệu (xem docs/07_database.md)."""

    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("email", name="uq_users_email"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    email: Mapped[str] = mapped_column(String(320))
    password_hash: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(server_default=text("true"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
