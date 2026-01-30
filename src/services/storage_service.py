from io import BytesIO
from minio import Minio
from minio.error import S3Error
from src.config.settings import get_settings
from src.exceptions import (
    FileDownloadError,
    FileUploadError,
    StorageConnectionError,
)


class StorageService:
    """MinIO client wrapper for document storage operations."""

    def __init__(self):
        settings = get_settings()

        self.clientMinio = Minio(
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
            if not self.clientMinio.bucket_exists(self.bucket_name):
                self.clientMinio.make_bucket(self.bucket_name)
        except S3Error as e:
            raise StorageConnectionError(
                self.clientMinio._base_url._url.geturl(),
                f"Failed to ensure bucket exists: {e}"
            ) from e

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
            FileUploadError: If the upload fails
        """
        try:
            self.clientMinio.put_object(
                self.bucket_name,
                object_key,
                BytesIO(file_data),
                file_size,
                content_type=content_type,
            )
            return object_key
        except S3Error as e:
            raise FileUploadError(object_key, self.bucket_name, e) from e

    def download_file(self, object_key: str) -> bytes:
        """Download a file from MinIO.

        Args:
            object_key: The path/key of the object in MinIO

        Returns:
            The file content as bytes

        Raises:
            FileDownloadError: If the download fails
        """
        response = None
        try:
            response = self.clientMinio.get_object(self.bucket_name, object_key)
            return response.read()
        except S3Error as e:
            raise FileDownloadError(object_key, self.bucket_name, e) from e
        finally:
            if response:
                response.close()
                response.release_conn()


    def is_available(self) -> bool:
        """Check if MinIO is available and accessible.

        Returns:
            True if MinIO is accessible, False otherwise
        """
        try:
            self.clientMinio.bucket_exists(self.bucket_name)
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
