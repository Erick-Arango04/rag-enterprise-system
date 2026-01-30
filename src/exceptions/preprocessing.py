"""Exceptions for document preprocessing (extraction and chunking)."""

from src.exceptions.base import RAGSystemError


class ExtractionError(RAGSystemError):
    """Base exception for document extraction errors."""

    def __init__(self, message: str, filename: str):
        self.filename = filename
        super().__init__(f"{message}: {filename}")


class CorruptedFileError(ExtractionError):
    """Raised when a file is corrupted or invalid."""

    def __init__(self, filename: str, message: str = "File is corrupted or invalid"):
        super().__init__(message, filename)


class UnsupportedFormatError(ExtractionError):
    """Raised when the file format is not supported."""

    def __init__(self, filename: str, content_type: str):
        message = f"Unsupported format: {content_type}"
        super().__init__(message, filename)


class ChunkingError(RAGSystemError):
    """Base exception for text chunking errors."""

    pass


class InvalidChunkConfigError(ChunkingError):
    """Raised when chunk configuration is invalid."""

    def __init__(self, chunk_size: int, chunk_overlap: int):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        message = f"chunk_overlap ({chunk_overlap}) must be less than chunk_size ({chunk_size})"
        super().__init__(message)
