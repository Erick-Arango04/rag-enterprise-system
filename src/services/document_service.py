from datetime import datetime, timezone

from fastapi import UploadFile
from sqlalchemy.orm import Session

from src.exceptions import (
    DocumentNotFoundError,
    FileUploadError,
    FileSizeExceededError,
    InvalidFileTypeError,
    StorageConnectionError,
)
from src.models.database import Document, DocumentChunk
from src.models.schemas import (
    ChunkResponse,
    DocumentChunksResponse,
    DocumentStatusResponse,
    UploadResponse,
)
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

    TEXT_PREVIEW_LENGTH = 200

    def __init__(self, db: Session, storage_service: StorageService | None = None):
        self.db = db
        self.storage_service = storage_service

    async def upload_document(self, file: UploadFile) -> UploadResponse:
        """Upload a document to storage and create database record.

        Args:
            file: The uploaded file from the request

        Returns:
            UploadResponse with document details

        Raises:
            InvalidFileTypeError: If MIME type is not allowed
            FileSizeExceededError: If file exceeds MAX_FILE_SIZE
            StorageConnectionError: If storage service is unavailable
            FileUploadError: If upload to storage fails
        """
        # If file.content_type is None → use default
        content_type = file.content_type or "application/octet-stream"
        filename = file.filename or "unknown"

        if content_type not in ALLOWED_MIME_TYPES:
            raise InvalidFileTypeError(
                filename=filename,
                content_type=content_type,
                allowed_types=list(ALLOWED_MIME_TYPES),
            )

        file_data = await file.read()
        file_size = len(file_data)

        if file_size > MAX_FILE_SIZE:
            raise FileSizeExceededError(
                filename=filename,
                file_size=file_size,
                max_size=MAX_FILE_SIZE,
            )

        if not self.storage_service.is_available():
            raise StorageConnectionError(
                endpoint="storage",
                message="Storage service is currently unavailable",
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
        except FileUploadError:
            self.db.rollback()
            raise

        return UploadResponse(
            doc_id=document.id,
            filename=document.filename,
            status=document.processing_status,
            minio_object_key=object_key,
        )

    def get_document_status(self, document_id: int) -> DocumentStatusResponse:
        """Get the processing status of a document.

        Args:
            document_id: The ID of the document to retrieve

        Returns:
            DocumentStatusResponse with document status and preview

        Raises:
            DocumentNotFoundError: If document does not exist
        """
        document = self.db.get(Document, document_id)
        if not document:
            raise DocumentNotFoundError(document_id)

        # Get text preview from first chunk
        text_preview = None
        if document.processing_status == "completed":
            first_chunk = (
                self.db.query(DocumentChunk)
                .filter(DocumentChunk.document_id == document_id)
                .order_by(DocumentChunk.chunk_index)
                .first()
            )
            if first_chunk:
                text_preview = first_chunk.content[: self.TEXT_PREVIEW_LENGTH]

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

    def get_document_chunks(self, document_id: int) -> DocumentChunksResponse:
        """Get all chunks for a document ordered by chunk_index.

        Args:
            document_id: The ID of the document

        Returns:
            DocumentChunksResponse with document info and chunk list

        Raises:
            DocumentNotFoundError: If document does not exist
        """
        document = self.db.get(Document, document_id)
        if not document:
            raise DocumentNotFoundError(document_id)

        chunks = (
            self.db.query(DocumentChunk)
            .filter(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.chunk_index)
            .all()
        )

        return DocumentChunksResponse(
            document_id=document.id,
            filename=document.filename,
            status=document.processing_status,
            total_chunks=len(chunks),
            chunks=[
                ChunkResponse(
                    id=chunk.id,
                    chunk_index=chunk.chunk_index,
                    content=chunk.content,
                    metadata=chunk.chunk_metadata,
                    created_at=chunk.created_at,
                )
                for chunk in chunks
            ],
        )
