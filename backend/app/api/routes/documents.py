import uuid
from typing import Literal

from fastapi import APIRouter, BackgroundTasks, Body, Depends, Query, Response, UploadFile, status

from app.api.dependencies import get_current_user, get_document_service, get_ingestion_service
from app.models.document import Document
from app.models.user import User
from app.schemas.document import DocumentListResponse, DocumentResponse, ReprocessRequest
from app.services.document_service import DocumentService
from app.services.ingestion_service import IngestionService

router = APIRouter(prefix="/documents", tags=["documents"])

DocumentStatus = Literal["uploaded", "processing", "ready", "failed"]


def _to_response(document: Document, chunk_count: int) -> DocumentResponse:
    response = DocumentResponse.model_validate(document)
    response.chunk_count = chunk_count
    return response


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_202_ACCEPTED)
def upload_document(
    file: UploadFile,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    service: DocumentService = Depends(get_document_service),
    ingestion: IngestionService = Depends(get_ingestion_service),
) -> DocumentResponse:
    document = service.upload(current_user, file.filename, file.file)
    # Xử lý (parse, chunk, embed) chạy sau khi đã trả 202; client theo dõi qua trường status.
    background_tasks.add_task(ingestion.process, document.id)
    return _to_response(document, service.count_chunks(current_user, document))


@router.get("", response_model=DocumentListResponse)
def list_documents(
    status_filter: DocumentStatus | None = Query(default=None, alias="status"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    service: DocumentService = Depends(get_document_service),
) -> DocumentListResponse:
    rows, total = service.list_documents(current_user, status=status_filter, limit=limit, offset=offset)
    return DocumentListResponse(
        items=[_to_response(document, chunk_count) for document, chunk_count in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: DocumentService = Depends(get_document_service),
) -> DocumentResponse:
    document, chunk_count = service.get_document(current_user, document_id)
    return _to_response(document, chunk_count)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: DocumentService = Depends(get_document_service),
) -> Response:
    service.delete_document(current_user, document_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{document_id}/reprocess", response_model=DocumentResponse, status_code=status.HTTP_202_ACCEPTED)
def reprocess_document(
    document_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    payload: ReprocessRequest | None = Body(default=None),
    current_user: User = Depends(get_current_user),
    service: DocumentService = Depends(get_document_service),
    ingestion: IngestionService = Depends(get_ingestion_service),
) -> DocumentResponse:
    options = payload or ReprocessRequest()
    document = service.start_reprocess(current_user, document_id)
    background_tasks.add_task(ingestion.process, document.id, options.chunk_size, options.chunk_overlap)
    return _to_response(document, service.count_chunks(current_user, document))
