"""Exceptions for background document processing."""

from src.exceptions.base import RAGSystemError


class ProcessingError(RAGSystemError):
    """Base exception for background processing operations."""

    pass


class DocumentProcessingError(ProcessingError):
    """Raised when document processing fails."""

    def __init__(self, document_id: int, stage: str, reason: str):
        self.document_id = document_id
        self.stage = stage
        super().__init__(f"Processing failed for document {document_id} at {stage}: {reason}")


class StatusUpdateError(ProcessingError):
    """Raised when updating document status fails."""

    def __init__(self, document_id: int, target_status: str, reason: str):
        self.document_id = document_id
        self.target_status = target_status
        super().__init__(
            f"Failed to update document {document_id} to status '{target_status}': {reason}"
        )
