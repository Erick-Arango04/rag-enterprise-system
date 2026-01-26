import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

from src.services.background_tasks import process_document_task
from src.models.database import Document


class TestProcessDocumentTask:
    """Unit tests for process_document_task background task."""

    @pytest.fixture
    def mock_document(self):
        """Create a mock document."""
        doc = MagicMock(spec=Document)
        doc.id = 1
        doc.filename = "test.pdf"
        doc.processing_status = "pending"
        doc.extracted_text = None
        doc.page_count = None
        doc.extraction_error = None
        doc.processed_at = None
        return doc

    @pytest.fixture
    def mock_db_session(self, mock_document):
        """Create a mock database session."""
        session = MagicMock()
        session.get.return_value = mock_document
        return session

    @pytest.fixture
    def mock_session_local(self, mock_db_session):
        """Create a mock SessionLocal factory."""
        session_local = MagicMock()
        session_local.return_value = mock_db_session
        return session_local

    def test_successful_extraction(self, mock_document, mock_db_session, mock_session_local):
        """Test successful document processing flow."""
        with patch("src.services.background_tasks.get_session_local") as mock_get_session:
            mock_get_session.return_value = mock_session_local

            with patch("src.services.background_tasks.StorageService") as mock_storage_class:
                mock_storage = MagicMock()
                mock_storage.download_file.return_value = b"file content"
                mock_storage_class.return_value = mock_storage

                with patch("src.services.background_tasks.DocumentExtractor") as mock_extractor_class:
                    mock_extractor = MagicMock()
                    mock_extractor.extract.return_value = ("Extracted text", 5, None)
                    mock_extractor_class.return_value = mock_extractor

                    process_document_task(
                        document_id=1,
                        minio_object_key="documents/2024/01/1_test.pdf",
                        content_type="application/pdf",
                    )

                    # Verify status was updated to processing
                    assert mock_document.processing_status == "processed"
                    assert mock_document.extracted_text == "Extracted text"
                    assert mock_document.page_count == 5
                    assert mock_document.processed_at is not None
                    mock_db_session.commit.assert_called()

    def test_document_not_found(self, mock_db_session, mock_session_local):
        """Test handling when document is not found."""
        mock_db_session.get.return_value = None

        with patch("src.services.background_tasks.get_session_local") as mock_get_session:
            mock_get_session.return_value = mock_session_local

            with patch("src.services.background_tasks.StorageService"):
                # Should return early without error
                process_document_task(
                    document_id=999,
                    minio_object_key="documents/2024/01/999_test.pdf",
                    content_type="application/pdf",
                )

                # Verify no extraction was attempted
                mock_db_session.close.assert_called_once()

    def test_extraction_failure(self, mock_document, mock_db_session, mock_session_local):
        """Test handling when extraction fails."""
        with patch("src.services.background_tasks.get_session_local") as mock_get_session:
            mock_get_session.return_value = mock_session_local

            with patch("src.services.background_tasks.StorageService") as mock_storage_class:
                mock_storage = MagicMock()
                mock_storage.download_file.return_value = b"corrupted content"
                mock_storage_class.return_value = mock_storage

                with patch("src.services.background_tasks.DocumentExtractor") as mock_extractor_class:
                    mock_extractor = MagicMock()
                    mock_extractor.extract.return_value = (None, None, "Failed to parse PDF")
                    mock_extractor_class.return_value = mock_extractor

                    process_document_task(
                        document_id=1,
                        minio_object_key="documents/2024/01/1_corrupted.pdf",
                        content_type="application/pdf",
                    )

                    assert mock_document.processing_status == "extraction_failed"
                    assert mock_document.extraction_error == "Failed to parse PDF"
                    assert mock_document.processed_at is not None
                    mock_db_session.commit.assert_called()

    def test_download_exception_handling(self, mock_document, mock_db_session, mock_session_local):
        """Test handling when MinIO download fails."""
        with patch("src.services.background_tasks.get_session_local") as mock_get_session:
            mock_get_session.return_value = mock_session_local

            with patch("src.services.background_tasks.StorageService") as mock_storage_class:
                mock_storage = MagicMock()
                mock_storage.download_file.side_effect = Exception("Connection refused")
                mock_storage_class.return_value = mock_storage

                process_document_task(
                    document_id=1,
                    minio_object_key="documents/2024/01/1_test.pdf",
                    content_type="application/pdf",
                )

                # Verify error status was set
                assert mock_document.processing_status == "error"
                assert "Connection refused" in mock_document.extraction_error
                mock_db_session.rollback.assert_called()

    def test_status_updated_to_processing(self, mock_document, mock_db_session, mock_session_local):
        """Test that status is set to 'processing' before extraction begins."""
        status_changes = []

        def track_status_change(value):
            status_changes.append(value)

        # Track status changes
        type(mock_document).processing_status = property(
            lambda self: status_changes[-1] if status_changes else "pending",
            lambda self, v: status_changes.append(v),
        )

        with patch("src.services.background_tasks.get_session_local") as mock_get_session:
            mock_get_session.return_value = mock_session_local

            with patch("src.services.background_tasks.StorageService") as mock_storage_class:
                mock_storage = MagicMock()
                mock_storage.download_file.return_value = b"content"
                mock_storage_class.return_value = mock_storage

                with patch("src.services.background_tasks.DocumentExtractor") as mock_extractor_class:
                    mock_extractor = MagicMock()
                    mock_extractor.extract.return_value = ("text", 1, None)
                    mock_extractor_class.return_value = mock_extractor

                    process_document_task(
                        document_id=1,
                        minio_object_key="key",
                        content_type="application/pdf",
                    )

                    # First status change should be "processing"
                    assert "processing" in status_changes
                    # Final status should be "processed"
                    assert status_changes[-1] == "processed"

    def test_db_session_always_closed(self, mock_document, mock_db_session, mock_session_local):
        """Test that database session is always closed, even on error."""
        with patch("src.services.background_tasks.get_session_local") as mock_get_session:
            mock_get_session.return_value = mock_session_local

            with patch("src.services.background_tasks.StorageService") as mock_storage_class:
                mock_storage = MagicMock()
                mock_storage.download_file.side_effect = Exception("Error")
                mock_storage_class.return_value = mock_storage

                process_document_task(
                    document_id=1,
                    minio_object_key="key",
                    content_type="application/pdf",
                )

                mock_db_session.close.assert_called_once()

    def test_extractor_receives_correct_arguments(self, mock_document, mock_db_session, mock_session_local):
        """Test that extractor receives correct file data and content type."""
        with patch("src.services.background_tasks.get_session_local") as mock_get_session:
            mock_get_session.return_value = mock_session_local

            with patch("src.services.background_tasks.StorageService") as mock_storage_class:
                mock_storage = MagicMock()
                mock_storage.download_file.return_value = b"pdf content"
                mock_storage_class.return_value = mock_storage

                with patch("src.services.background_tasks.DocumentExtractor") as mock_extractor_class:
                    mock_extractor = MagicMock()
                    mock_extractor.extract.return_value = ("text", 1, None)
                    mock_extractor_class.return_value = mock_extractor

                    process_document_task(
                        document_id=1,
                        minio_object_key="documents/2024/01/1_test.pdf",
                        content_type="application/pdf",
                    )

                    mock_extractor.extract.assert_called_once_with(
                        b"pdf content",
                        "application/pdf",
                        "test.pdf",
                    )
