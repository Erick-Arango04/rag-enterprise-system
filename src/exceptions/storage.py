"""Exceptions for storage operations (MinIO/S3)."""

from src.exceptions.base import RAGSystemError


class StorageError(RAGSystemError):
    """Base exception for storage operations."""

    pass


class StorageConnectionError(StorageError):
    """Raised when unable to connect to storage service."""

    def __init__(self, endpoint: str, message: str = "Failed to connect to storage service"):
        self.endpoint = endpoint
        super().__init__(f"{message}: {endpoint}")


class BucketNotFoundError(StorageError):
    """Raised when the specified bucket does not exist."""

    def __init__(self, bucket_name: str):
        self.bucket_name = bucket_name
        super().__init__(f"Bucket not found: {bucket_name}")


class FileUploadError(StorageError):
    """Raised when file upload fails."""

    def __init__(self, filename: str, bucket: str, reason: str = "Upload failed"):
        self.filename = filename
        self.bucket = bucket
        super().__init__(f"{reason} for '{filename}' to bucket '{bucket}'")


class FileDownloadError(StorageError):
    """Raised when file download fails."""

    def __init__(self, object_key: str, bucket: str, reason: str = "Download failed"):
        self.object_key = object_key
        self.bucket = bucket
        super().__init__(f"{reason} for '{object_key}' from bucket '{bucket}'")
