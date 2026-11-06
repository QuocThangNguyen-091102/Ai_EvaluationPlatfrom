import uuid

from fastapi import APIRouter, Depends, Query, Response, UploadFile, status

from app.api.dependencies import get_current_user, get_dataset_service
from app.models.dataset import DatasetVersion
from app.models.user import User
from app.schemas.dataset import (
    DatasetCreate,
    DatasetListResponse,
    DatasetResponse,
    DatasetVersionListResponse,
    DatasetVersionResponse,
    Difficulty,
    ImportResult,
    QuestionType,
    TestCaseInput,
    TestCaseListResponse,
    TestCaseResponse,
    VersionCreate,
)
from app.services.dataset_service import DatasetService

router = APIRouter(tags=["datasets"])


def _version(version: DatasetVersion, count: int) -> DatasetVersionResponse:
    return DatasetVersionResponse(
        id=version.id,
        dataset_id=version.dataset_id,
        version_number=version.version_number,
        status=version.status,
        reviewed_at=version.reviewed_at,
        notes=version.notes,
        created_at=version.created_at,
        test_case_count=count,
    )


@router.post("/datasets", response_model=DatasetResponse, status_code=status.HTTP_201_CREATED)
def create_dataset(payload: DatasetCreate, user: User = Depends(get_current_user), service: DatasetService = Depends(get_dataset_service)):
    return service.create_dataset(user, payload.name, payload.description)


@router.get("/datasets", response_model=DatasetListResponse)
def list_datasets(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user),
    service: DatasetService = Depends(get_dataset_service),
) -> DatasetListResponse:
    items, total = service.list_datasets(user, limit=limit, offset=offset)
    return DatasetListResponse(items=[DatasetResponse.model_validate(i) for i in items], total=total, limit=limit, offset=offset)


@router.get("/datasets/{dataset_id}", response_model=DatasetResponse)
def get_dataset(dataset_id: uuid.UUID, user: User = Depends(get_current_user), service: DatasetService = Depends(get_dataset_service)):
    return service.get_dataset(user, dataset_id)


@router.post("/datasets/{dataset_id}/versions", response_model=DatasetVersionResponse, status_code=status.HTTP_201_CREATED)
def create_version(
    dataset_id: uuid.UUID,
    payload: VersionCreate | None = None,
    user: User = Depends(get_current_user),
    service: DatasetService = Depends(get_dataset_service),
) -> DatasetVersionResponse:
    payload = payload or VersionCreate()
    version, count = service.create_version(user, dataset_id, payload.copy_from_version_id, payload.notes)
    return _version(version, count)


@router.get("/datasets/{dataset_id}/versions", response_model=DatasetVersionListResponse)
def list_versions(dataset_id: uuid.UUID, user: User = Depends(get_current_user), service: DatasetService = Depends(get_dataset_service)):
    return DatasetVersionListResponse(items=[_version(v, c) for v, c in service.list_versions(user, dataset_id)])


@router.post("/dataset-versions/{version_id}/review", response_model=DatasetVersionResponse)
def review_version(version_id: uuid.UUID, user: User = Depends(get_current_user), service: DatasetService = Depends(get_dataset_service)):
    version, count = service.review_version(user, version_id)
    return _version(version, count)


@router.get("/dataset-versions/{version_id}/test-cases", response_model=TestCaseListResponse)
def list_test_cases(
    version_id: uuid.UUID,
    question_type: QuestionType | None = None,
    difficulty: Difficulty | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user),
    service: DatasetService = Depends(get_dataset_service),
) -> TestCaseListResponse:
    items, total = service.list_cases(user, version_id, question_type=question_type, difficulty=difficulty, limit=limit, offset=offset)
    return TestCaseListResponse(items=[TestCaseResponse.model_validate(i) for i in items], total=total, limit=limit, offset=offset)


@router.post("/dataset-versions/{version_id}/test-cases", response_model=TestCaseResponse, status_code=status.HTTP_201_CREATED)
def add_test_case(
    version_id: uuid.UUID, payload: TestCaseInput, user: User = Depends(get_current_user), service: DatasetService = Depends(get_dataset_service)
):
    return service.add_case(user, version_id, payload)


@router.post("/dataset-versions/{version_id}/test-cases/import", response_model=ImportResult)
def import_test_cases(
    version_id: uuid.UUID, file: UploadFile, user: User = Depends(get_current_user), service: DatasetService = Depends(get_dataset_service)
) -> ImportResult:
    content = file.file.read(2 * 1024 * 1024 + 1)
    return ImportResult(imported=service.import_cases(user, version_id, file.filename, content))


@router.put("/test-cases/{case_id}", response_model=TestCaseResponse)
def update_test_case(
    case_id: uuid.UUID, payload: TestCaseInput, user: User = Depends(get_current_user), service: DatasetService = Depends(get_dataset_service)
):
    return service.update_case(user, case_id, payload)


@router.delete("/test-cases/{case_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_test_case(case_id: uuid.UUID, user: User = Depends(get_current_user), service: DatasetService = Depends(get_dataset_service)) -> Response:
    service.delete_case(user, case_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
