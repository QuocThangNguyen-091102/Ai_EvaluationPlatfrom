import uuid

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.model_config import ModelConfiguration


class DuplicateConfigurationNameError(Exception):
    pass


class ModelConfigRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_for_user(self, user_id: uuid.UUID, config_id: uuid.UUID) -> ModelConfiguration | None:
        return self._session.scalar(
            select(ModelConfiguration).where(ModelConfiguration.id == config_id, ModelConfiguration.user_id == user_id)
        )

    def get_by_name(self, user_id: uuid.UUID, name: str) -> ModelConfiguration | None:
        return self._session.scalar(
            select(ModelConfiguration).where(ModelConfiguration.user_id == user_id, ModelConfiguration.name == name)
        )

    def list_for_user(self, user_id: uuid.UUID, *, limit: int, offset: int) -> tuple[list[ModelConfiguration], int]:
        total = self._session.scalar(
            select(func.count()).select_from(ModelConfiguration).where(ModelConfiguration.user_id == user_id)
        )
        items = self._session.scalars(
            select(ModelConfiguration)
            .where(ModelConfiguration.user_id == user_id)
            .order_by(ModelConfiguration.created_at.desc(), ModelConfiguration.id)
            .limit(limit)
            .offset(offset)
        ).all()
        return list(items), total

    def add(self, config: ModelConfiguration) -> ModelConfiguration:
        self._session.add(config)
        try:
            self._session.flush()
        except IntegrityError as error:
            self._session.rollback()
            raise DuplicateConfigurationNameError(config.name) from error
        return config

    def commit(self) -> None:
        self._session.commit()
