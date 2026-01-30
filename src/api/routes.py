from fastapi import APIRouter, BackgroundTasks, Depends, File, Path, UploadFile
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.models.schemas import (
    DocumentChunksResponse,
    DocumentStatusResponse,
    ErrorResponse,
    UploadResponse,
)
from src.services.background_tasks import process_document_task
from src.services.document_service import DocumentService
from src.services.storage_service import StorageService, get_storage_service


router = APIRouter(prefix="/api/v1", tags=["documents"])


@router.post(
    "/upload",
    response_model=UploadResponse,
    status_code=201,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid file type"},
        413: {"model": ErrorResponse, "description": "File too large"},
        503: {"model": ErrorResponse, "description": "Storage unavailable"},
    },
)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    storage_service: StorageService = Depends(get_storage_service),
) -> UploadResponse:
    """Upload a document for processing.

    Accepts PDF, DOCX, TXT, and MD files up to 50MB.
    """
    service = DocumentService(db, storage_service)
    result = await service.upload_document(file)

    background_tasks.add_task(
        process_document_task,
        document_id=result.doc_id,
        minio_object_key=result.minio_object_key,
        content_type=file.content_type or "application/octet-stream",
    )

    return result


@router.get(
    "/documents/{document_id}",
    response_model=DocumentStatusResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Document not found"},
    },
)
async def get_document_status(
    document_id: int = Path(..., gt=0),
    db: Session = Depends(get_db),
) -> DocumentStatusResponse:
    """Get the processing status of a document.

    Returns:
        Document status including processing state and text preview if available
    """
    service = DocumentService(db)
    return service.get_document_status(document_id)


@router.get(
    "/documents/{document_id}/chunks",
    response_model=DocumentChunksResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Document not found"},
    },
)
async def get_document_chunks(
    document_id: int = Path(..., gt=0),
    db: Session = Depends(get_db),
) -> DocumentChunksResponse:
    """Get all chunks for a document ordered by chunk_index.

    Returns:
        Document info and list of chunks with their content and metadata
    """
    service = DocumentService(db)
    return service.get_document_chunks(document_id)
