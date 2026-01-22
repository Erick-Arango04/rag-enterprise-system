from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

# Dependency Injection
from src.config.database import get_db
from src.models.schemas import UploadResponse
from src.services.document_service import DocumentService
from src.services.storage_service import get_storage_service, StorageService

#Creates a route organizer separate from the main FastAPI app
router = APIRouter(prefix="/api/v1", tags=["documents"]) # tag for OpenAPI/Swagger


@router.post("/upload", response_model=UploadResponse, status_code=201)
async def upload_document(
    #parameter_name: Type = Source(config)
    file: UploadFile = File(...),
    db: Session = Depends(get_db), # Dependency Injection with Depends()
    storage_service: StorageService = Depends(get_storage_service), # Dependency Injection with Depends()
) -> UploadResponse:
    """Upload a document for processing.

    Accepts PDF, DOCX, TXT, and MD files up to 50MB.
    """

    ## MyClass obj = new MyClass();
    service = DocumentService(db, storage_service)
    return await service.upload_document(file)
