"""FastAPI exception handlers for RAG system custom exceptions."""

import traceback
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from src.exceptions import (
    RAGSystemError,
    DocumentNotFoundError,
    InvalidFileTypeError,
    FileSizeExceededError,
    StorageConnectionError,
    BucketNotFoundError,
    FileUploadError,
    FileDownloadError,
    ExtractionError,
    CorruptedFileError,
    UnsupportedFormatError,
    ChunkingError,
    InvalidChunkConfigError,
    DocumentProcessingError,
    StatusUpdateError,
)
from src.utils.logging import get_logger, log_request_error

logger = get_logger(__name__)


def _build_error_response(
    error_type: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a standardized error response dictionary."""
    response: dict[str, Any] = {
        "error_type": error_type,
        "message": message,
    }
    if details:
        response["details"] = details
    return response


# Document Exception Handlers


async def document_not_found_handler(
    request: Request, exc: DocumentNotFoundError
) -> JSONResponse:
    """Handle DocumentNotFoundError - returns 404."""
    log_request_error(
        logger,
        event="document_not_found",
        error_type="DocumentNotFoundError",
        error_message=exc.message,
        doc_id=exc.document_id,
    )
    return JSONResponse(
        status_code=404,
        content=_build_error_response(
            error_type="DocumentNotFoundError",
            message=exc.message,
            details={"document_id": exc.document_id},
        ),
    )


async def invalid_file_type_handler(
    request: Request, exc: InvalidFileTypeError
) -> JSONResponse:
    """Handle InvalidFileTypeError - returns 400."""
    log_request_error(
        logger,
        event="invalid_file_type",
        error_type="InvalidFileTypeError",
        error_message=exc.message,
        filename=exc.filename,
        content_type=exc.content_type,
        allowed_types=exc.allowed_types,
    )
    return JSONResponse(
        status_code=400,
        content=_build_error_response(
            error_type="InvalidFileTypeError",
            message=exc.message,
            details={
                "filename": exc.filename,
                "content_type": exc.content_type,
                "allowed_types": exc.allowed_types,
            },
        ),
    )


async def file_size_exceeded_handler(
    request: Request, exc: FileSizeExceededError
) -> JSONResponse:
    """Handle FileSizeExceededError - returns 413."""
    log_request_error(
        logger,
        event="file_size_exceeded",
        error_type="FileSizeExceededError",
        error_message=exc.message,
        filename=exc.filename,
        file_size=exc.file_size,
        max_size=exc.max_size,
    )
    return JSONResponse(
        status_code=413,
        content=_build_error_response(
            error_type="FileSizeExceededError",
            message=exc.message,
            details={
                "filename": exc.filename,
                "file_size": exc.file_size,
                "max_size": exc.max_size,
            },
        ),
    )


# Storage Exception Handlers


async def storage_connection_error_handler(
    request: Request, exc: StorageConnectionError
) -> JSONResponse:
    """Handle StorageConnectionError - returns 503."""
    log_request_error(
        logger,
        event="storage_connection_failed",
        error_type="StorageConnectionError",
        error_message=exc.message,
        endpoint=exc.endpoint,
        stack_trace=traceback.format_exc(),
    )
    return JSONResponse(
        status_code=503,
        content=_build_error_response(
            error_type="StorageConnectionError",
            message="Storage service is currently unavailable",
            details={"endpoint": exc.endpoint},
        ),
    )


async def bucket_not_found_handler(
    request: Request, exc: BucketNotFoundError
) -> JSONResponse:
    """Handle BucketNotFoundError - returns 503."""
    log_request_error(
        logger,
        event="bucket_not_found",
        error_type="BucketNotFoundError",
        error_message=exc.message,
        bucket_name=exc.bucket_name,
        stack_trace=traceback.format_exc(),
    )
    return JSONResponse(
        status_code=503,
        content=_build_error_response(
            error_type="BucketNotFoundError",
            message="Storage service is misconfigured",
            details={"bucket_name": exc.bucket_name},
        ),
    )


async def file_upload_error_handler(
    request: Request, exc: FileUploadError
) -> JSONResponse:
    """Handle FileUploadError - returns 503."""
    log_request_error(
        logger,
        event="file_upload_failed",
        error_type="FileUploadError",
        error_message=exc.message,
        filename=exc.filename,
        bucket=exc.bucket,
        stack_trace=traceback.format_exc(),
    )
    return JSONResponse(
        status_code=503,
        content=_build_error_response(
            error_type="FileUploadError",
            message="Failed to upload file to storage",
            details={"filename": exc.filename, "bucket": exc.bucket},
        ),
    )


async def file_download_error_handler(
    request: Request, exc: FileDownloadError
) -> JSONResponse:
    """Handle FileDownloadError - returns 503."""
    log_request_error(
        logger,
        event="file_download_failed",
        error_type="FileDownloadError",
        error_message=exc.message,
        object_key=exc.object_key,
        bucket=exc.bucket,
        stack_trace=traceback.format_exc(),
    )
    return JSONResponse(
        status_code=503,
        content=_build_error_response(
            error_type="FileDownloadError",
            message="Failed to download file from storage",
            details={"object_key": exc.object_key, "bucket": exc.bucket},
        ),
    )


# Preprocessing Exception Handlers


async def corrupted_file_error_handler(
    request: Request, exc: CorruptedFileError
) -> JSONResponse:
    """Handle CorruptedFileError - returns 422."""
    log_request_error(
        logger,
        event="corrupted_file",
        error_type="CorruptedFileError",
        error_message=exc.message,
        filename=exc.filename,
    )
    return JSONResponse(
        status_code=422,
        content=_build_error_response(
            error_type="CorruptedFileError",
            message=exc.message,
            details={"filename": exc.filename},
        ),
    )


async def unsupported_format_error_handler(
    request: Request, exc: UnsupportedFormatError
) -> JSONResponse:
    """Handle UnsupportedFormatError - returns 415."""
    log_request_error(
        logger,
        event="unsupported_format",
        error_type="UnsupportedFormatError",
        error_message=exc.message,
        filename=exc.filename,
    )
    return JSONResponse(
        status_code=415,
        content=_build_error_response(
            error_type="UnsupportedFormatError",
            message=exc.message,
            details={"filename": exc.filename},
        ),
    )


async def extraction_error_handler(
    request: Request, exc: ExtractionError
) -> JSONResponse:
    """Handle generic ExtractionError - returns 422."""
    log_request_error(
        logger,
        event="extraction_failed",
        error_type="ExtractionError",
        error_message=exc.message,
        filename=exc.filename,
        stack_trace=traceback.format_exc(),
    )
    return JSONResponse(
        status_code=422,
        content=_build_error_response(
            error_type="ExtractionError",
            message=exc.message,
            details={"filename": exc.filename},
        ),
    )


async def invalid_chunk_config_handler(
    request: Request, exc: InvalidChunkConfigError
) -> JSONResponse:
    """Handle InvalidChunkConfigError - returns 500."""
    log_request_error(
        logger,
        event="invalid_chunk_config",
        error_type="InvalidChunkConfigError",
        error_message=exc.message,
        chunk_size=exc.chunk_size,
        chunk_overlap=exc.chunk_overlap,
        stack_trace=traceback.format_exc(),
    )
    return JSONResponse(
        status_code=500,
        content=_build_error_response(
            error_type="InvalidChunkConfigError",
            message="Internal configuration error",
            details={
                "chunk_size": exc.chunk_size,
                "chunk_overlap": exc.chunk_overlap,
            },
        ),
    )


async def chunking_error_handler(
    request: Request, exc: ChunkingError
) -> JSONResponse:
    """Handle generic ChunkingError - returns 500."""
    log_request_error(
        logger,
        event="chunking_failed",
        error_type="ChunkingError",
        error_message=exc.message,
        stack_trace=traceback.format_exc(),
    )
    return JSONResponse(
        status_code=500,
        content=_build_error_response(
            error_type="ChunkingError",
            message="Document chunking failed",
        ),
    )


# Processing Exception Handlers


async def document_processing_error_handler(
    request: Request, exc: DocumentProcessingError
) -> JSONResponse:
    """Handle DocumentProcessingError - returns 500."""
    log_request_error(
        logger,
        event="document_processing_failed",
        error_type="DocumentProcessingError",
        error_message=exc.message,
        doc_id=exc.document_id,
        stage=exc.stage,
        stack_trace=traceback.format_exc(),
    )
    return JSONResponse(
        status_code=500,
        content=_build_error_response(
            error_type="DocumentProcessingError",
            message="Document processing failed",
            details={
                "document_id": exc.document_id,
                "stage": exc.stage,
            },
        ),
    )


async def status_update_error_handler(
    request: Request, exc: StatusUpdateError
) -> JSONResponse:
    """Handle StatusUpdateError - returns 500."""
    log_request_error(
        logger,
        event="status_update_failed",
        error_type="StatusUpdateError",
        error_message=exc.message,
        doc_id=exc.document_id,
        target_status=exc.target_status,
        stack_trace=traceback.format_exc(),
    )
    return JSONResponse(
        status_code=500,
        content=_build_error_response(
            error_type="StatusUpdateError",
            message="Failed to update document status",
            details={
                "document_id": exc.document_id,
                "target_status": exc.target_status,
            },
        ),
    )


# Fallback Handler


async def rag_system_error_handler(
    request: Request, exc: RAGSystemError
) -> JSONResponse:
    """Handle any unhandled RAGSystemError - returns 500."""
    log_request_error(
        logger,
        event="rag_system_error",
        error_type=type(exc).__name__,
        error_message=exc.message,
        stack_trace=traceback.format_exc(),
    )
    return JSONResponse(
        status_code=500,
        content=_build_error_response(
            error_type=type(exc).__name__,
            message="An internal error occurred",
        ),
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register all exception handlers with the FastAPI application.

    Order matters: more specific exceptions must be registered before
    their parent classes to ensure proper handling.
    """
    # Document exceptions
    app.add_exception_handler(DocumentNotFoundError, document_not_found_handler)
    app.add_exception_handler(InvalidFileTypeError, invalid_file_type_handler)
    app.add_exception_handler(FileSizeExceededError, file_size_exceeded_handler)

    # Storage exceptions (specific first)
    app.add_exception_handler(StorageConnectionError, storage_connection_error_handler)
    app.add_exception_handler(BucketNotFoundError, bucket_not_found_handler)
    app.add_exception_handler(FileUploadError, file_upload_error_handler)
    app.add_exception_handler(FileDownloadError, file_download_error_handler)

    # Preprocessing exceptions (specific first)
    app.add_exception_handler(CorruptedFileError, corrupted_file_error_handler)
    app.add_exception_handler(UnsupportedFormatError, unsupported_format_error_handler)
    app.add_exception_handler(ExtractionError, extraction_error_handler)
    app.add_exception_handler(InvalidChunkConfigError, invalid_chunk_config_handler)
    app.add_exception_handler(ChunkingError, chunking_error_handler)

# Processing exceptions
    app.add_exception_handler(
        DocumentProcessingError, document_processing_error_handler
    )
    app.add_exception_handler(StatusUpdateError, status_update_error_handler)

    # Fallback for any RAGSystemError not caught above
    app.add_exception_handler(RAGSystemError, rag_system_error_handler)
