"""Background tasks for document processing."""
import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from src.config.database import get_session_local
from src.exceptions import (
    DocumentProcessingError,
    FileDownloadError,
    StatusUpdateError,
)
from src.models.database import Document, DocumentChunk
from src.preprocessing.chunking import TextChunker
from src.preprocessing.extractors import DocumentExtractor
from src.services.storage_service import StorageService

logger = logging.getLogger(__name__)


def process_document_task(
    document_id: int,
    minio_object_key: str,
    content_type: str,
) -> None:
    """Background task to process document extraction.

    Args:
        document_id: The ID of the document to process
        minio_object_key: The MinIO object key for the file
        content_type: The MIME type of the file
    """
    SessionLocal = get_session_local()
    db: Session = SessionLocal()
    storage_service = StorageService()

    try:
        logger.info(f"Starting text extraction for document {document_id}")

        # Update status to processing
        document = db.get(Document, document_id)
        if not document:
            logger.error(f"Document {document_id} not found")
            return

        document.processing_status = "processing"
        db.commit()

        # Download file from MinIO
        logger.info(f"Downloading file from MinIO: {minio_object_key}")
        file_data = storage_service.download_file(minio_object_key)

        # Extract text
        extractor = DocumentExtractor()
        extracted_text, page_count, error = extractor.extract(
            file_data, content_type, document.filename
        )

        # Update document with results
        if error:
            logger.warning(f"Extraction failed for document {document_id}: {error}")
            document.processing_status = "extraction_failed"
            document.extraction_error = error
        else:
            logger.info(f"Text extraction complete for document {document_id}")
            document.extracted_text = extracted_text
            document.page_count = page_count

            # Chunk the extracted text
            logger.info(f"Starting chunking for document {document_id}")
            chunker = TextChunker()
            chunk_records = chunker.chunk_to_db_records(
                extracted_text,
                document_id=document_id,
                extra_metadata={"filename": document.filename}
            )

            # Store chunks in database
            for record in chunk_records:
                chunk = DocumentChunk(
                    document_id=record["document_id"],
                    chunk_index=record["chunk_index"],
                    content=record["content"],
                    chunk_metadata=record["metadata"],
                )
                db.add(chunk)

            document.processing_status = "completed"
            logger.info(f"Document {document_id} completed: {len(chunk_records)} chunks created")

        document.processed_at = datetime.now(timezone.utc)
        db.commit()

    except FileDownloadError as e:
        logger.error(f"Download failed for document {document_id}: {e}")
        db.rollback()
        _update_document_error(db, document_id, "error", e)
    except DocumentProcessingError as e:
        logger.error(f"Processing failed for document {document_id}: {e}")
        db.rollback()
        _update_document_error(db, document_id, "error", e)
    except Exception as e:
        logger.error(f"Unexpected error processing document {document_id}: {e}")
        db.rollback()
        _update_document_error(db, document_id, "error", e)
    finally:
        db.close()


def _update_document_error(
    db: Session, document_id: int, status: str, error: str | Exception
) -> None:
    """Update document with error status.

    Args:
        db: Database session
        document_id: The document ID to update
        status: The status to set
        error: The error message or exception
    """
    error_message = str(error) if isinstance(error, Exception) else error
    try:
        document = db.get(Document, document_id)
        if document:
            document.processing_status = status
            document.extraction_error = error_message
            document.processed_at = datetime.now(timezone.utc)
            db.commit()
    except Exception as e:
        logger.error(f"Failed to update document {document_id} status: {e}")
        db.rollback()
        raise StatusUpdateError(document_id, status, str(e)) from e
