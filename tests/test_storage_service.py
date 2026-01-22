import pytest
from unittest.mock import MagicMock, patch
from minio.error import S3Error

from src.services.storage_service import StorageService


class TestStorageService:
    """Unit tests for StorageService."""

    @pytest.fixture
    def mock_minio_client(self):
        """Create a mock MinIO client."""
        with patch("src.services.storage_service.Minio") as mock_minio:
            mock_client = MagicMock()
            mock_minio.return_value = mock_client
            mock_client.bucket_exists.return_value = True
            yield mock_client

    @pytest.fixture
    def storage_service(self, mock_minio_client):
        """Create a StorageService with mocked MinIO client."""
        with patch("src.services.storage_service.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                minio_endpoint="localhost:9000",
                minio_access_key="minioadmin",
                minio_secret_key="minioadmin123",
                minio_secure=False,
                minio_bucket="documents",
            )
            service = StorageService()
            service.client = mock_minio_client
            return service

    def test_upload_file_success(self, storage_service, mock_minio_client):
        """Test successful file upload to MinIO."""
        object_key = "documents/1/test.pdf"
        file_data = b"test content"
        file_size = len(file_data)
        content_type = "application/pdf"

        result = storage_service.upload_file(object_key, file_data, file_size, content_type)

        assert result == object_key
        mock_minio_client.put_object.assert_called_once()

    def test_upload_file_minio_error(self, storage_service, mock_minio_client):
        """Test S3Error is raised when MinIO fails."""
        mock_minio_client.put_object.side_effect = S3Error(
            "PutObject",
            "NoSuchBucket",
            "The specified bucket does not exist",
            "PUT",
            {},
            None,
            None,
        )

        with pytest.raises(S3Error):
            storage_service.upload_file(
                "documents/1/test.pdf", b"content", 7, "application/pdf"
            )

    def test_is_available_returns_true(self, storage_service, mock_minio_client):
        """Test availability check when MinIO is up."""
        mock_minio_client.bucket_exists.return_value = True

        assert storage_service.is_available() is True

    def test_is_available_returns_false(self, storage_service, mock_minio_client):
        """Test availability check when MinIO is down."""
        mock_minio_client.bucket_exists.side_effect = Exception("Connection error")

        assert storage_service.is_available() is False

    def test_ensure_bucket_creates_if_missing(self, mock_minio_client):
        """Test bucket creation on initialization."""
        mock_minio_client.bucket_exists.return_value = False

        with patch("src.services.storage_service.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                minio_endpoint="localhost:9000",
                minio_access_key="minioadmin",
                minio_secret_key="minioadmin123",
                minio_secure=False,
                minio_bucket="documents",
            )
            service = StorageService()
            service.client = mock_minio_client

        mock_minio_client.make_bucket.assert_called_once_with("documents")
