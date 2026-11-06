import uuid

from fastapi import APIRouter, Depends, Query, status

from app.api.dependencies import get_current_user, get_model_config_service
from app.models.user import User
from app.schemas.model_config import (
    ModelConfigurationCreate,
    ModelConfigurationListResponse,
    ModelConfigurationResponse,
    ServerCapabilities,
)
from app.services.model_config_service import ModelConfigService

router = APIRouter(prefix="/model-configurations", tags=["model-configurations"])


@router.get("/capabilities", response_model=ServerCapabilities)
def get_capabilities(
    _: User = Depends(get_current_user), service: ModelConfigService = Depends(get_model_config_service)
) -> ServerCapabilities:
    return service.capabilities()


@router.post("", response_model=ModelConfigurationResponse, status_code=status.HTTP_201_CREATED)
def create_configuration(
    payload: ModelConfigurationCreate,
    current_user: User = Depends(get_current_user),
    service: ModelConfigService = Depends(get_model_config_service),
):
    return service.create(current_user, payload)


@router.get("", response_model=ModelConfigurationListResponse)
def list_configurations(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    service: ModelConfigService = Depends(get_model_config_service),
) -> ModelConfigurationListResponse:
    items, total = service.list(current_user, limit=limit, offset=offset)
    return ModelConfigurationListResponse(
        items=[ModelConfigurationResponse.model_validate(item) for item in items], total=total, limit=limit, offset=offset
    )


@router.get("/{config_id}", response_model=ModelConfigurationResponse)
def get_configuration(
    config_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: ModelConfigService = Depends(get_model_config_service),
):
    return service.get(current_user, config_id)
