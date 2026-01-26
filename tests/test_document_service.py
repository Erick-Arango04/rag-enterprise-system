import pytest
from unittest.mock import MagicMock, AsyncMock
from fastapi import HTTPException, UploadFile
from starlette.datastructures import Headers
from io import BytesIO
from minio.error import S3Error

from src.services.document_service import DocumentService, MAX_FILE_SIZE, ALLOWED_MIME_TYPES
from src.models.database import Document


class TestDocumentService:
    """Unit tests for DocumentService."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        db = MagicMock()
        db.flush = MagicMock()
        db.commit = MagicMock()
        db.rollback = MagicMock()
        db.add = MagicMock()
        return db

    @pytest.fixture
    def mock_storage(self):
        """Create a mock storage service."""
        storage = MagicMock()
        storage.is_available.return_value = True
        storage.upload_file.return_value = "documents/1/test.pdf"
        return storage

    @pytest.fixture
    def service(self, mock_db, mock_storage):
        """Create a DocumentService with mocks."""
        return DocumentService(mock_db, mock_storage)

    def _create_upload_file(self, filename: str, content: bytes, content_type: str) -> UploadFile:
        """Helper to create UploadFile objects."""
        headers = Headers({"content-type": content_type})
        return UploadFile(filename=filename, file=BytesIO(content), headers=headers)

    # MIME validation tests
    @pytest.mark.asyncio
    async def test_upload_valid_pdf(self, service, mock_db):
        """Test PDF upload succeeds."""
        mock_db.flush.side_effect = lambda: setattr(
            mock_db.add.call_args[0][0], "id", 1
        )
        file = self._create_upload_file("test.pdf", b"content", "application/pdf")

        result = await service.upload_document(file)

        assert result.filename == "test.pdf"
        assert result.status == "pending"

    @pytest.mark.asyncio
    async def test_upload_valid_docx(self, service, mock_db):
        """Test DOCX upload succeeds."""
        mock_db.flush.side_effect = lambda: setattr(
            mock_db.add.call_args[0][0], "id", 1
        )
        file = self._create_upload_file(
            "test.docx",
            b"content",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )

        result = await service.upload_document(file)

        assert result.filename == "test.docx"

    @pytest.mark.asyncio
    async def test_upload_valid_txt(self, service, mock_db):
        """Test plain text upload succeeds."""
        mock_db.flush.side_effect = lambda: setattr(
            mock_db.add.call_args[0][0], "id", 1
        )
        file = self._create_upload_file("test.txt", b"Hello world", "text/plain")

        result = await service.upload_document(file)

        assert result.filename == "test.txt"

    @pytest.mark.asyncio
    async def test_upload_valid_markdown(self, service, mock_db):
        """Test markdown upload succeeds."""
        mock_db.flush.side_effect = lambda: setattr(
            mock_db.add.call_args[0][0], "id", 1
        )
        file = self._create_upload_file("test.md", b"# Hello", "text/markdown")

        result = await service.upload_document(file)

        assert result.filename == "test.md"

    @pytest.mark.asyncio
    async def test_upload_invalid_mime_type_raises_400(self, service):
        """Test invalid MIME type returns 400."""
        file = self._create_upload_file("test.png", b"content", "image/png")

        with pytest.raises(HTTPException) as exc_info:
            await service.upload_document(file)

        assert exc_info.value.status_code == 400
        assert "Invalid file type" in exc_info.value.detail

    # Size validation tests
    @pytest.mark.asyncio
    async def test_upload_file_under_limit(self, service, mock_db):
        """Test file under 50MB succeeds."""
        mock_db.flush.side_effect = lambda: setattr(
            mock_db.add.call_args[0][0], "id", 1
        )
        file = self._create_upload_file("test.pdf", b"x" * 1024, "application/pdf")

        result = await service.upload_document(file)

        assert result.doc_id == 1

    @pytest.mark.asyncio
    async def test_upload_file_over_limit_raises_413(self, service):
        """Test file over 50MB returns 413."""
        large_content = b"x" * (MAX_FILE_SIZE + 1)
        file = self._create_upload_file("large.pdf", large_content, "application/pdf")

        with pytest.raises(HTTPException) as exc_info:
            await service.upload_document(file)

        assert exc_info.value.status_code == 413
        assert "File too large" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_upload_file_exactly_at_limit(self, service, mock_db):
        """Test file at exactly 50MB succeeds."""
        mock_db.flush.side_effect = lambda: setattr(
            mock_db.add.call_args[0][0], "id", 1
        )
        content = b"x" * MAX_FILE_SIZE
        file = self._create_upload_file("exact.pdf", content, "application/pdf")

        result = await service.upload_document(file)

        assert result.doc_id == 1

    # MinIO availability tests
    @pytest.mark.asyncio
    async def test_upload_minio_unavailable_raises_503(self, mock_db):
        """Test MinIO unavailable returns 503."""
        mock_storage = MagicMock()
        mock_storage.is_available.return_value = False
        service = DocumentService(mock_db, mock_storage)
        file = self._create_upload_file("test.pdf", b"content", "application/pdf")

        with pytest.raises(HTTPException) as exc_info:
            await service.upload_document(file)

        assert exc_info.value.status_code == 503
        assert "Storage service is currently unavailable" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_upload_minio_error_rollback(self, mock_db, mock_storage):
        """Test database rollback when MinIO upload fails."""
        mock_db.flush.side_effect = lambda: setattr(
            mock_db.add.call_args[0][0], "id", 1
        )
        mock_storage.upload_file.side_effect = S3Error(
            "PutObject", "Error", "Upload failed", "PUT", {}, None, None
        )
        service = DocumentService(mock_db, mock_storage)
        file = self._create_upload_file("test.pdf", b"content", "application/pdf")

        with pytest.raises(HTTPException) as exc_info:
            await service.upload_document(file)

        assert exc_info.value.status_code == 503
        mock_db.rollback.assert_called_once()

    # Database tests
    @pytest.mark.asyncio
    async def test_document_record_created(self, service, mock_db):
        """Test document record is inserted with correct fields."""
        mock_db.flush.side_effect = lambda: setattr(
            mock_db.add.call_args[0][0], "id", 1
        )
        file = self._create_upload_file("test.pdf", b"content", "application/pdf")

        await service.upload_document(file)

        mock_db.add.assert_called_once()
        added_doc = mock_db.add.call_args[0][0]
        assert added_doc.filename == "test.pdf"
        assert added_doc.content_type == "application/pdf"
        assert added_doc.processing_status == "pending"

    @pytest.mark.asyncio
    async def test_minio_object_key_format(self, service, mock_db, mock_storage):
        """Test MinIO path is documents/{year}/{month}/{doc_id}_{filename}."""
        mock_db.flush.side_effect = lambda: setattr(
            mock_db.add.call_args[0][0], "id", 42
        )
        file = self._create_upload_file("test.pdf", b"content", "application/pdf")

        await service.upload_document(file)

        mock_storage.upload_file.assert_called_once()
        call_args = mock_storage.upload_file.call_args[0]
        object_key = call_args[0]
        # Verify date-based path format: documents/{year}/{month}/{doc_id}_{filename}
        import re
        pattern = r"^documents/\d{4}/\d{2}/42_test\.pdf$"
        assert re.match(pattern, object_key), f"Object key '{object_key}' doesn't match expected format"
