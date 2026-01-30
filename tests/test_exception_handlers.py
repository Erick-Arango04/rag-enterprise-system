"""Unit tests for FastAPI exception handlers."""

import json
import pytest
from unittest.mock import MagicMock

from fastapi import Request

from src.api.exception_handlers import (
    document_not_found_handler,
    invalid_file_type_handler,
    file_size_exceeded_handler,
    storage_connection_error_handler,
    bucket_not_found_handler,
    file_upload_error_handler,
    file_download_error_handler,
    corrupted_file_error_handler,
    unsupported_format_error_handler,
    extraction_error_handler,
    invalid_chunk_config_handler,
    chunking_error_handler,
    document_processing_error_handler,
    status_update_error_handler,
    rag_system_error_handler,
)
from src.exceptions import (
    RAGSystemError,
    DocumentNotFoundError,
    InvalidFileTypeError,
    FileSizeExceededError,
    StorageConnectionError,
    BucketNotFoundError,
    FileUploadError,
    FileDownloadError,
    CorruptedFileError,
    UnsupportedFormatError,
    ExtractionError,
    ChunkingError,
    InvalidChunkConfigError,
    DocumentProcessingError,
    StatusUpdateError,
)


@pytest.fixture
def mock_request():
    """Create a mock FastAPI request."""
    return MagicMock(spec=Request)


class TestDocumentNotFoundHandler:
    """Tests for DocumentNotFoundError handler."""

    @pytest.mark.asyncio
    async def test_returns_404_status_code(self, mock_request):
        exc = DocumentNotFoundError(42)
        response = await document_not_found_handler(mock_request, exc)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_response_contains_error_type(self, mock_request):
        exc = DocumentNotFoundError(42)
        response = await document_not_found_handler(mock_request, exc)
        body = json.loads(response.body)
        assert body["error_type"] == "DocumentNotFoundError"

    @pytest.mark.asyncio
    async def test_response_contains_document_id(self, mock_request):
        exc = DocumentNotFoundError(42)
        response = await document_not_found_handler(mock_request, exc)
        body = json.loads(response.body)
        assert body["details"]["document_id"] == 42


class TestInvalidFileTypeHandler:
    """Tests for InvalidFileTypeError handler."""

    @pytest.mark.asyncio
    async def test_returns_400_status_code(self, mock_request):
        exc = InvalidFileTypeError("test.png", "image/png", ["application/pdf"])
        response = await invalid_file_type_handler(mock_request, exc)
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_response_contains_file_details(self, mock_request):
        exc = InvalidFileTypeError("test.png", "image/png", ["application/pdf"])
        response = await invalid_file_type_handler(mock_request, exc)
        body = json.loads(response.body)
        assert body["details"]["filename"] == "test.png"
        assert body["details"]["content_type"] == "image/png"
        assert body["details"]["allowed_types"] == ["application/pdf"]


class TestFileSizeExceededHandler:
    """Tests for FileSizeExceededError handler."""

    @pytest.mark.asyncio
    async def test_returns_413_status_code(self, mock_request):
        exc = FileSizeExceededError("large.pdf", 100_000_000, 50_000_000)
        response = await file_size_exceeded_handler(mock_request, exc)
        assert response.status_code == 413

    @pytest.mark.asyncio
    async def test_response_contains_size_details(self, mock_request):
        exc = FileSizeExceededError("large.pdf", 100_000_000, 50_000_000)
        response = await file_size_exceeded_handler(mock_request, exc)
        body = json.loads(response.body)
        assert body["details"]["filename"] == "large.pdf"
        assert body["details"]["file_size"] == 100_000_000
        assert body["details"]["max_size"] == 50_000_000


class TestStorageConnectionErrorHandler:
    """Tests for StorageConnectionError handler."""

    @pytest.mark.asyncio
    async def test_returns_503_status_code(self, mock_request):
        exc = StorageConnectionError("localhost:9000")
        response = await storage_connection_error_handler(mock_request, exc)
        assert response.status_code == 503

    @pytest.mark.asyncio
    async def test_response_contains_endpoint(self, mock_request):
        exc = StorageConnectionError("localhost:9000")
        response = await storage_connection_error_handler(mock_request, exc)
        body = json.loads(response.body)
        assert body["details"]["endpoint"] == "localhost:9000"


class TestBucketNotFoundHandler:
    """Tests for BucketNotFoundError handler."""

    @pytest.mark.asyncio
    async def test_returns_503_status_code(self, mock_request):
        exc = BucketNotFoundError("documents")
        response = await bucket_not_found_handler(mock_request, exc)
        assert response.status_code == 503

    @pytest.mark.asyncio
    async def test_response_contains_bucket_name(self, mock_request):
        exc = BucketNotFoundError("documents")
        response = await bucket_not_found_handler(mock_request, exc)
        body = json.loads(response.body)
        assert body["details"]["bucket_name"] == "documents"


class TestFileUploadErrorHandler:
    """Tests for FileUploadError handler."""

    @pytest.mark.asyncio
    async def test_returns_503_status_code(self, mock_request):
        exc = FileUploadError("test.pdf", "documents")
        response = await file_upload_error_handler(mock_request, exc)
        assert response.status_code == 503

    @pytest.mark.asyncio
    async def test_response_contains_file_details(self, mock_request):
        exc = FileUploadError("test.pdf", "documents")
        response = await file_upload_error_handler(mock_request, exc)
        body = json.loads(response.body)
        assert body["details"]["filename"] == "test.pdf"
        assert body["details"]["bucket"] == "documents"


class TestFileDownloadErrorHandler:
    """Tests for FileDownloadError handler."""

    @pytest.mark.asyncio
    async def test_returns_503_status_code(self, mock_request):
        exc = FileDownloadError("documents/test.pdf", "documents")
        response = await file_download_error_handler(mock_request, exc)
        assert response.status_code == 503

    @pytest.mark.asyncio
    async def test_response_contains_object_details(self, mock_request):
        exc = FileDownloadError("documents/test.pdf", "documents")
        response = await file_download_error_handler(mock_request, exc)
        body = json.loads(response.body)
        assert body["details"]["object_key"] == "documents/test.pdf"
        assert body["details"]["bucket"] == "documents"


class TestCorruptedFileErrorHandler:
    """Tests for CorruptedFileError handler."""

    @pytest.mark.asyncio
    async def test_returns_422_status_code(self, mock_request):
        exc = CorruptedFileError("test.pdf")
        response = await corrupted_file_error_handler(mock_request, exc)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_response_contains_filename(self, mock_request):
        exc = CorruptedFileError("test.pdf")
        response = await corrupted_file_error_handler(mock_request, exc)
        body = json.loads(response.body)
        assert body["details"]["filename"] == "test.pdf"


class TestUnsupportedFormatErrorHandler:
    """Tests for UnsupportedFormatError handler."""

    @pytest.mark.asyncio
    async def test_returns_415_status_code(self, mock_request):
        exc = UnsupportedFormatError("test.xyz", "application/xyz")
        response = await unsupported_format_error_handler(mock_request, exc)
        assert response.status_code == 415


class TestExtractionErrorHandler:
    """Tests for ExtractionError handler."""

    @pytest.mark.asyncio
    async def test_returns_422_status_code(self, mock_request):
        exc = ExtractionError("Extraction failed", "test.pdf")
        response = await extraction_error_handler(mock_request, exc)
        assert response.status_code == 422


class TestInvalidChunkConfigHandler:
    """Tests for InvalidChunkConfigError handler."""

    @pytest.mark.asyncio
    async def test_returns_500_status_code(self, mock_request):
        exc = InvalidChunkConfigError(100, 200)
        response = await invalid_chunk_config_handler(mock_request, exc)
        assert response.status_code == 500

    @pytest.mark.asyncio
    async def test_response_contains_config_details(self, mock_request):
        exc = InvalidChunkConfigError(100, 200)
        response = await invalid_chunk_config_handler(mock_request, exc)
        body = json.loads(response.body)
        assert body["details"]["chunk_size"] == 100
        assert body["details"]["chunk_overlap"] == 200


class TestChunkingErrorHandler:
    """Tests for ChunkingError handler."""

    @pytest.mark.asyncio
    async def test_returns_500_status_code(self, mock_request):
        exc = ChunkingError("Chunking failed")
        response = await chunking_error_handler(mock_request, exc)
        assert response.status_code == 500


class TestDocumentProcessingErrorHandler:
    """Tests for DocumentProcessingError handler."""

    @pytest.mark.asyncio
    async def test_returns_500_status_code(self, mock_request):
        exc = DocumentProcessingError(1, "extraction", "Failed")
        response = await document_processing_error_handler(mock_request, exc)
        assert response.status_code == 500

    @pytest.mark.asyncio
    async def test_response_contains_processing_details(self, mock_request):
        exc = DocumentProcessingError(1, "extraction", "Failed")
        response = await document_processing_error_handler(mock_request, exc)
        body = json.loads(response.body)
        assert body["details"]["document_id"] == 1
        assert body["details"]["stage"] == "extraction"


class TestStatusUpdateErrorHandler:
    """Tests for StatusUpdateError handler."""

    @pytest.mark.asyncio
    async def test_returns_500_status_code(self, mock_request):
        exc = StatusUpdateError(1, "completed", "DB error")
        response = await status_update_error_handler(mock_request, exc)
        assert response.status_code == 500

    @pytest.mark.asyncio
    async def test_response_contains_status_details(self, mock_request):
        exc = StatusUpdateError(1, "completed", "DB error")
        response = await status_update_error_handler(mock_request, exc)
        body = json.loads(response.body)
        assert body["details"]["document_id"] == 1
        assert body["details"]["target_status"] == "completed"


class TestFallbackHandler:
    """Tests for RAGSystemError fallback handler."""

    @pytest.mark.asyncio
    async def test_returns_500_status_code(self, mock_request):
        exc = RAGSystemError("Unknown error")
        response = await rag_system_error_handler(mock_request, exc)
        assert response.status_code == 500

    @pytest.mark.asyncio
    async def test_response_contains_generic_message(self, mock_request):
        exc = RAGSystemError("Unknown error")
        response = await rag_system_error_handler(mock_request, exc)
        body = json.loads(response.body)
        assert body["message"] == "An internal error occurred"
