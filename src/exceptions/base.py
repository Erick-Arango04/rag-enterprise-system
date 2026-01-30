"""Base exception classes for the RAG system."""


class RAGSystemError(Exception):
    """Base exception for all RAG system errors.

    All custom exceptions in the system should inherit from this class
    to enable consistent error handling and catching.
    """

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)
