from fastapi import APIRouter, Depends, UploadFile, status

from app.api.dependencies import get_current_user, get_document_service
from app.models.user import User
from app.schemas.document import DocumentResponse
from app.services.document_service import DocumentService

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_202_ACCEPTED)
def upload_document(
    file: UploadFile,
    current_user: User = Depends(get_current_user),
    service: DocumentService = Depends(get_document_service),
) -> DocumentResponse:
    document = service.upload(current_user, file.filename, file.file)
    response = DocumentResponse.model_validate(document)
    response.chunk_count = service.count_chunks(current_user, document)
    return response
