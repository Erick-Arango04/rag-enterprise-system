from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Path, UploadFile
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.models.database import Document
from src.models.schemas import DocumentStatusResponse, UploadResponse
from src.services.background_tasks import process_document_task
from src.services.document_service import DocumentService
from src.services.storage_service import StorageService, get_storage_service

router = APIRouter(prefix="/api/v1", tags=["documents"])


@router.post("/upload", response_model=UploadResponse, status_code=201)
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

    # Launch background task for text extraction
    background_tasks.add_task(
        process_document_task,
        document_id=result.doc_id,
        minio_object_key=result.minio_object_key,
        content_type=file.content_type or "application/octet-stream",
    )

    return result


@router.get("/documents/{document_id}", response_model=DocumentStatusResponse)
async def get_document_status(
    document_id: int = Path(..., gt=0),
    db: Session = Depends(get_db),
) -> DocumentStatusResponse:
    """Get the processing status of a document.

    Returns:
        Document status including processing state and text preview if available
    """
    document = db.get(Document, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    text_preview = None
    if document.extracted_text:
        text_preview = document.extracted_text[:200]

    return DocumentStatusResponse(
        id=document.id,
        filename=document.filename,
        status=document.processing_status,
        page_count=document.page_count,
        text_preview=text_preview,
        error=document.extraction_error,
        processed_at=document.processed_at,
        upload_timestamp=document.upload_timestamp,
    )
