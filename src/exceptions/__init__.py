"""Custom exceptions for the RAG system.

This module provides a comprehensive exception hierarchy for all
components of the RAG system, enabling consistent error handling.
"""

from src.exceptions.base import RAGSystemError
from src.exceptions.document import (
    DocumentError,
    DocumentNotFoundError,
    FileSizeExceededError,
    InvalidFileTypeError,
)
from src.exceptions.preprocessing import (
    ChunkingError,
    CorruptedFileError,
    ExtractionError,
    InvalidChunkConfigError,
    UnsupportedFormatError,
)
from src.exceptions.processing import (
    DocumentProcessingError,
    ProcessingError,
    StatusUpdateError,
)
from src.exceptions.storage import (
    BucketNotFoundError,
    FileDownloadError,
    FileUploadError,
    StorageConnectionError,
    StorageError,
)

__all__ = [
    # Base
    "RAGSystemError",
    # Preprocessing
    "ExtractionError",
    "CorruptedFileError",
    "UnsupportedFormatError",
    "ChunkingError",
    "InvalidChunkConfigError",
    # Storage
    "StorageError",
    "StorageConnectionError",
    "BucketNotFoundError",
    "FileUploadError",
    "FileDownloadError",
    # Document
    "DocumentError",
    "DocumentNotFoundError",
    "InvalidFileTypeError",
    "FileSizeExceededError",
    # Processing
    "ProcessingError",
    "DocumentProcessingError",
    "StatusUpdateError",
]
