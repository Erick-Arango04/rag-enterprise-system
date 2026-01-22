from io import BytesIO
from minio import Minio
from minio.error import S3Error
from src.config.settings import get_settings


class StorageService:
    """MinIO client wrapper for document storage operations."""

    def __init__(self):
        settings = get_settings()

        self.client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
        )

        self.bucket_name = settings.minio_bucket
        self._ensure_bucket_exists()

    def _ensure_bucket_exists(self) -> None:
        """Create the bucket if it doesn't exist."""
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
        except S3Error:
            pass

    def upload_file(
        self, object_key: str, file_data: bytes, file_size: int, content_type: str
    ) -> str:
        """Upload a file to MinIO.

        Args:
            object_key: The path/key for the object in MinIO
            file_data: The file content as bytes
            file_size: The size of the file in bytes
            content_type: The MIME type of the file

        Returns:
            The object key where the file was stored

        Raises:
            S3Error: If the upload fails
        """
        self.client.put_object(
            self.bucket_name,
            object_key,
            BytesIO(file_data),
            file_size,
            content_type=content_type,
        )
        return object_key

    def is_available(self) -> bool:
        """Check if MinIO is available and accessible."""
        try:
            self.client.bucket_exists(self.bucket_name)
            return True
        except Exception:
            return False


_storage_service: StorageService | None = None


def get_storage_service() -> StorageService:
    """Get or create the storage service singleton."""
    global _storage_service
    if _storage_service is None:
        _storage_service = StorageService()
    return _storage_service
