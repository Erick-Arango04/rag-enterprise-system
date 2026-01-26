"""Background tasks for document processing."""
import logging
from datetime import datetime,timezone

from sqlalchemy.orm import Session

from src.config.database import get_session_local
from src.models.database import Document
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
            logger.info(f"Document {document_id} processed successfully")
            document.processing_status = "processed"
            document.extracted_text = extracted_text
            document.page_count = page_count

        document.processed_at = datetime.now(timezone.utc)
        db.commit()

    except Exception as e:
        logger.error(f"Error processing document {document_id}: {str(e)}")
        db.rollback()
        try:
            document = db.get(Document, document_id)
            if document:
                document.processing_status = "error"
                document.extraction_error = str(e)
                document.processed_at = datetime.now(timezone.utc)
                db.commit()
        except Exception:
            db.rollback()
    finally:
        db.close()
