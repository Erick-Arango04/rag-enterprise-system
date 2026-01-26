"""Custom exceptions for document extraction."""


class ExtractionError(Exception):
    """Base exception for document extraction errors."""

    def __init__(self, message: str, filename: str):
        self.message = message
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
