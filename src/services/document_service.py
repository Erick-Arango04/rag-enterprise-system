from datetime import datetime, timezone

from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session
from minio.error import S3Error

from src.models.database import Document
from src.models.schemas import UploadResponse
from src.services.storage_service import StorageService


MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

#A set of allowed file types
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
    "text/markdown",
}


class DocumentService:
    """Business logic for document operations."""

    def __init__(self, db: Session, storage_service: StorageService):
        self.db = db
        self.storage_service = storage_service

    async def upload_document(self, file: UploadFile) -> UploadResponse:
        """Upload a document to storage and create database record.

        Args:
            file: The uploaded file from the request

        Returns:
            UploadResponse with document details

        Raises:
            HTTPException: 400 if invalid MIME type, 413 if file too large,
                          503 if storage unavailable
        """

        # If file.content_type is None → use default
        content_type = file.content_type or "application/octet-stream"
        if content_type not in ALLOWED_MIME_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type: {content_type}. Allowed: PDF, DOCX, TXT, MD",
            )

        file_data = await file.read()
        file_size = len(file_data)

        if file_size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"File too large: {file_size} bytes. Max: 50MB",
            )

        if not self.storage_service.is_available():
            raise HTTPException(
                status_code=503,
                detail="Storage service is currently unavailable",
            )

        document = Document(
            filename=file.filename,
            content_type=content_type,
            file_size=file_size,
            processing_status="pending",
        )
        self.db.add(document)
        self.db.flush()

        now = datetime.now(timezone.utc)
        object_key = f"documents/{now.year}/{now.month:02d}/{document.id}_{file.filename}"

        try:
            self.storage_service.upload_file(
                object_key, file_data, file_size, content_type
            )
            document.minio_object_key = object_key
            self.db.commit()
        except S3Error:
            self.db.rollback()
            raise HTTPException(
                status_code=503,
                detail="Storage service is currently unavailable",
            )

        return UploadResponse(
            doc_id=document.id,
            filename=document.filename,
            status=document.processing_status,
            minio_object_key=object_key,
        )
