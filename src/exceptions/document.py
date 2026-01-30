"""Exceptions for document service operations."""

from src.exceptions.base import RAGSystemError


class DocumentError(RAGSystemError):
    """Base exception for document service operations."""

    pass


class DocumentNotFoundError(DocumentError):
    """Raised when a document is not found."""

    def __init__(self, document_id: int):
        self.document_id = document_id
        super().__init__(f"Document not found: {document_id}")


class InvalidFileTypeError(DocumentError):
    """Raised when the file type is not allowed."""

    def __init__(self, filename: str, content_type: str, allowed_types: list[str]):
        self.filename = filename
        self.content_type = content_type
        self.allowed_types = allowed_types
        super().__init__(
            f"Invalid file type '{content_type}' for '{filename}'. "
            f"Allowed types: {', '.join(allowed_types)}"
        )


class FileSizeExceededError(DocumentError):
    """Raised when the file exceeds the maximum allowed size."""

    def __init__(self, filename: str, file_size: int, max_size: int):
        self.filename = filename
        self.file_size = file_size
        self.max_size = max_size
        super().__init__(
            f"File '{filename}' size ({file_size} bytes) exceeds maximum allowed ({max_size} bytes)"
        )
