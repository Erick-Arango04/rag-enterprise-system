"""Background tasks for document processing."""
import logging
from datetime import datetime, timezone
from typing import List

from sqlalchemy.orm import Session

from src.config.database import get_session_local
from src.exceptions import (
    CorruptedFileError,
    DocumentProcessingError,
    FileDownloadError,
    StatusUpdateError,
    UnsupportedFormatError,
)
from src.models.database import Document, DocumentChunk
from src.preprocessing.chunking import TextChunker
from src.preprocessing.extractors import DocumentExtractor
from src.services.storage_service import StorageService

logger = logging.getLogger(__name__)

# Batch size for database inserts
CHUNK_BATCH_SIZE = 50


def process_document_task(
    document_id: int,
    minio_object_key: str,
    content_type: str,
) -> None:
    """Background task to process document extraction using streaming.

    Processes documents page-by-page for memory efficiency, saving chunks
    in batches as they are produced.

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

        # Process using streaming pipeline
        extractor = DocumentExtractor()
        chunker = TextChunker()

        chunk_batch: List[DocumentChunk] = []
        total_chunks = 0
        page_count = 0

        try:
            # Stream pages and chunks
            pages_generator = extractor.extract_pages(
                file_data, content_type, document.filename
            )

            for chunk in chunker.chunk_streaming(pages_generator):
                # Track page count from chunk metadata
                if chunk.metadata and "page_number" in chunk.metadata:
                    page_count = max(page_count, chunk.metadata["page_number"])

                # Create database record
                db_chunk = DocumentChunk(
                    document_id=document_id,
                    chunk_index=chunk.chunk_index,
                    content=chunk.content,
                    chunk_metadata={
                        "start_char": chunk.start_char,
                        "end_char": chunk.end_char,
                        "filename": document.filename,
                        **(chunk.metadata or {}),
                    },
                )
                chunk_batch.append(db_chunk)
                total_chunks += 1

                # Batch insert when batch is full
                if len(chunk_batch) >= CHUNK_BATCH_SIZE:
                    _save_chunk_batch(db, chunk_batch)
                    chunk_batch = []

            # Save remaining chunks
            if chunk_batch:
                _save_chunk_batch(db, chunk_batch)

            # Update document status
            document.page_count = page_count if page_count > 0 else 1
            document.processing_status = "completed"
            document.processed_at = datetime.now(timezone.utc)
            db.commit()

            logger.info(
                f"Document {document_id} completed: {total_chunks} chunks created "
                f"from {page_count} pages"
            )

        except (UnsupportedFormatError, CorruptedFileError) as e:
            logger.warning(f"Extraction failed for document {document_id}: {e}")
            document.processing_status = "extraction_failed"
            document.extraction_error = str(e)
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


def _save_chunk_batch(db: Session, chunks: List[DocumentChunk]) -> None:
    """Save a batch of chunks to the database.

    Args:
        db: Database session
        chunks: List of DocumentChunk objects to save
    """
    for chunk in chunks:
        db.add(chunk)
    db.flush()


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
