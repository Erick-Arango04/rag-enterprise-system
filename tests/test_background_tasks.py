import pytest
from unittest.mock import MagicMock, patch

from src.services.background_tasks import process_document_task
from src.models.database import Document, DocumentChunk
from src.preprocessing.extractors import PageContent
from src.models.chunk import TextChunk


class TestProcessDocumentTask:
    """Unit tests for process_document_task background task with streaming."""

    @pytest.fixture
    def mock_document(self):
        """Create a mock document."""
        doc = MagicMock(spec=Document)
        doc.id = 1
        doc.filename = "test.pdf"
        doc.processing_status = "pending"
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

    def _create_mock_pages(self, texts):
        """Helper to create mock PageContent objects."""
        total = len(texts)
        for i, text in enumerate(texts):
            yield PageContent(
                text=text,
                page_number=i + 1,
                total_pages=total,
                is_last=(i == total - 1),
            )

    def _create_mock_chunks(self, contents):
        """Helper to create mock TextChunk objects."""
        for i, content in enumerate(contents):
            yield TextChunk(
                content=content,
                chunk_index=i,
                start_char=i * 100,
                end_char=(i + 1) * 100,
                metadata={"page_number": 1},
            )

    def test_successful_extraction_with_streaming(self, mock_document, mock_db_session, mock_session_local):
        """Test successful document processing with streaming pipeline."""
        added_objects = []
        mock_db_session.add.side_effect = lambda obj: added_objects.append(obj)

        with patch("src.services.background_tasks.get_session_local") as mock_get_session:
            mock_get_session.return_value = mock_session_local

            with patch("src.services.background_tasks.StorageService") as mock_storage_class:
                mock_storage = MagicMock()
                mock_storage.download_file.return_value = b"file content"
                mock_storage_class.return_value = mock_storage

                with patch("src.services.background_tasks.DocumentExtractor") as mock_extractor_class:
                    mock_extractor = MagicMock()
                    mock_extractor.extract_pages.return_value = self._create_mock_pages(
                        ["Page 1 text", "Page 2 text"]
                    )
                    mock_extractor_class.return_value = mock_extractor

                    with patch("src.services.background_tasks.TextChunker") as mock_chunker_class:
                        mock_chunker = MagicMock()
                        mock_chunker.chunk_streaming.return_value = self._create_mock_chunks(
                            ["chunk1", "chunk2", "chunk3"]
                        )
                        mock_chunker_class.return_value = mock_chunker

                        process_document_task(
                            document_id=1,
                            minio_object_key="documents/2024/01/1_test.pdf",
                            content_type="application/pdf",
                        )

                        # Verify status was updated to completed
                        assert mock_document.processing_status == "completed"
                        assert mock_document.page_count == 1  # From chunk metadata
                        assert mock_document.processed_at is not None

                        # Verify chunks were created
                        chunk_adds = [obj for obj in added_objects if isinstance(obj, DocumentChunk)]
                        assert len(chunk_adds) == 3

    def test_document_not_found(self, mock_db_session, mock_session_local):
        """Test handling when document is not found."""
        mock_db_session.get.return_value = None

        with patch("src.services.background_tasks.get_session_local") as mock_get_session:
            mock_get_session.return_value = mock_session_local

            with patch("src.services.background_tasks.StorageService"):
                process_document_task(
                    document_id=999,
                    minio_object_key="documents/2024/01/999_test.pdf",
                    content_type="application/pdf",
                )

                mock_db_session.close.assert_called_once()

    def test_extraction_failure_unsupported_format(self, mock_document, mock_db_session, mock_session_local):
        """Test handling when extraction fails due to unsupported format."""
        from src.exceptions import UnsupportedFormatError

        with patch("src.services.background_tasks.get_session_local") as mock_get_session:
            mock_get_session.return_value = mock_session_local

            with patch("src.services.background_tasks.StorageService") as mock_storage_class:
                mock_storage = MagicMock()
                mock_storage.download_file.return_value = b"content"
                mock_storage_class.return_value = mock_storage

                with patch("src.services.background_tasks.DocumentExtractor") as mock_extractor_class:
                    mock_extractor = MagicMock()
                    mock_extractor.extract_pages.side_effect = UnsupportedFormatError(
                        "test.xyz", "application/unknown"
                    )
                    mock_extractor_class.return_value = mock_extractor

                    process_document_task(
                        document_id=1,
                        minio_object_key="documents/2024/01/1_test.xyz",
                        content_type="application/unknown",
                    )

                    assert mock_document.processing_status == "extraction_failed"
                    assert "Unsupported format" in mock_document.extraction_error

    def test_extraction_failure_corrupted_file(self, mock_document, mock_db_session, mock_session_local):
        """Test handling when extraction fails due to corrupted file."""
        from src.exceptions import CorruptedFileError

        with patch("src.services.background_tasks.get_session_local") as mock_get_session:
            mock_get_session.return_value = mock_session_local

            with patch("src.services.background_tasks.StorageService") as mock_storage_class:
                mock_storage = MagicMock()
                mock_storage.download_file.return_value = b"corrupted"
                mock_storage_class.return_value = mock_storage

                with patch("src.services.background_tasks.DocumentExtractor") as mock_extractor_class:
                    mock_extractor = MagicMock()
                    mock_extractor.extract_pages.side_effect = CorruptedFileError(
                        "test.pdf", "Failed to parse PDF"
                    )
                    mock_extractor_class.return_value = mock_extractor

                    process_document_task(
                        document_id=1,
                        minio_object_key="documents/2024/01/1_corrupted.pdf",
                        content_type="application/pdf",
                    )

                    assert mock_document.processing_status == "extraction_failed"
                    assert "Failed to parse PDF" in mock_document.extraction_error

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

                assert mock_document.processing_status == "error"
                assert "Connection refused" in mock_document.extraction_error
                mock_db_session.rollback.assert_called()

    def test_status_updated_to_processing(self, mock_document, mock_db_session, mock_session_local):
        """Test that status is set to 'processing' before extraction begins."""
        status_changes = []

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
                    mock_extractor.extract_pages.return_value = self._create_mock_pages(["text"])
                    mock_extractor_class.return_value = mock_extractor

                    with patch("src.services.background_tasks.TextChunker") as mock_chunker_class:
                        mock_chunker = MagicMock()
                        mock_chunker.chunk_streaming.return_value = self._create_mock_chunks(["chunk"])
                        mock_chunker_class.return_value = mock_chunker

                        process_document_task(
                            document_id=1,
                            minio_object_key="key",
                            content_type="application/pdf",
                        )

                        assert "processing" in status_changes
                        assert status_changes[-1] == "completed"

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
        """Test that extractor.extract_pages receives correct arguments."""
        with patch("src.services.background_tasks.get_session_local") as mock_get_session:
            mock_get_session.return_value = mock_session_local

            with patch("src.services.background_tasks.StorageService") as mock_storage_class:
                mock_storage = MagicMock()
                mock_storage.download_file.return_value = b"pdf content"
                mock_storage_class.return_value = mock_storage

                with patch("src.services.background_tasks.DocumentExtractor") as mock_extractor_class:
                    mock_extractor = MagicMock()
                    mock_extractor.extract_pages.return_value = iter([])
                    mock_extractor_class.return_value = mock_extractor

                    with patch("src.services.background_tasks.TextChunker") as mock_chunker_class:
                        mock_chunker = MagicMock()
                        mock_chunker.chunk_streaming.return_value = iter([])
                        mock_chunker_class.return_value = mock_chunker

                        process_document_task(
                            document_id=1,
                            minio_object_key="documents/2024/01/1_test.pdf",
                            content_type="application/pdf",
                        )

                        mock_extractor.extract_pages.assert_called_once_with(
                            b"pdf content",
                            "application/pdf",
                            "test.pdf",
                        )

    def test_chunks_created_with_correct_metadata(self, mock_document, mock_db_session, mock_session_local):
        """Test that chunks are created with correct metadata."""
        added_objects = []
        mock_db_session.add.side_effect = lambda obj: added_objects.append(obj)

        with patch("src.services.background_tasks.get_session_local") as mock_get_session:
            mock_get_session.return_value = mock_session_local

            with patch("src.services.background_tasks.StorageService") as mock_storage_class:
                mock_storage = MagicMock()
                mock_storage.download_file.return_value = b"content"
                mock_storage_class.return_value = mock_storage

                with patch("src.services.background_tasks.DocumentExtractor") as mock_extractor_class:
                    mock_extractor = MagicMock()
                    mock_extractor.extract_pages.return_value = self._create_mock_pages(["text"])
                    mock_extractor_class.return_value = mock_extractor

                    with patch("src.services.background_tasks.TextChunker") as mock_chunker_class:
                        mock_chunker = MagicMock()
                        mock_chunker.chunk_streaming.return_value = self._create_mock_chunks(["chunk"])
                        mock_chunker_class.return_value = mock_chunker

                        process_document_task(
                            document_id=1,
                            minio_object_key="documents/2024/01/1_test.pdf",
                            content_type="application/pdf",
                        )

                        chunk_adds = [obj for obj in added_objects if isinstance(obj, DocumentChunk)]
                        assert len(chunk_adds) == 1
                        chunk = chunk_adds[0]
                        assert chunk.document_id == 1
                        assert chunk.chunk_index == 0
                        assert chunk.content == "chunk"
                        assert "filename" in chunk.chunk_metadata
                        assert chunk.chunk_metadata["filename"] == "test.pdf"

    def test_batch_processing_flushes_chunks(self, mock_document, mock_db_session, mock_session_local):
        """Test that chunks are flushed in batches."""
        added_objects = []
        mock_db_session.add.side_effect = lambda obj: added_objects.append(obj)

        with patch("src.services.background_tasks.get_session_local") as mock_get_session:
            mock_get_session.return_value = mock_session_local

            with patch("src.services.background_tasks.StorageService") as mock_storage_class:
                mock_storage = MagicMock()
                mock_storage.download_file.return_value = b"content"
                mock_storage_class.return_value = mock_storage

                with patch("src.services.background_tasks.DocumentExtractor") as mock_extractor_class:
                    mock_extractor = MagicMock()
                    mock_extractor.extract_pages.return_value = self._create_mock_pages(["text"])
                    mock_extractor_class.return_value = mock_extractor

                    with patch("src.services.background_tasks.TextChunker") as mock_chunker_class:
                        mock_chunker = MagicMock()
                        # Create 60 chunks to trigger batch flush (batch size is 50)
                        mock_chunker.chunk_streaming.return_value = self._create_mock_chunks(
                            [f"chunk{i}" for i in range(60)]
                        )
                        mock_chunker_class.return_value = mock_chunker

                        process_document_task(
                            document_id=1,
                            minio_object_key="documents/2024/01/1_test.pdf",
                            content_type="application/pdf",
                        )

                        # Verify flush was called (at least once for batch)
                        assert mock_db_session.flush.call_count >= 1
                        # Verify all 60 chunks were added
                        chunk_adds = [obj for obj in added_objects if isinstance(obj, DocumentChunk)]
                        assert len(chunk_adds) == 60

    def test_empty_extraction_completes_successfully(self, mock_document, mock_db_session, mock_session_local):
        """Test that empty extraction (no chunks) completes successfully."""
        with patch("src.services.background_tasks.get_session_local") as mock_get_session:
            mock_get_session.return_value = mock_session_local

            with patch("src.services.background_tasks.StorageService") as mock_storage_class:
                mock_storage = MagicMock()
                mock_storage.download_file.return_value = b"content"
                mock_storage_class.return_value = mock_storage

                with patch("src.services.background_tasks.DocumentExtractor") as mock_extractor_class:
                    mock_extractor = MagicMock()
                    mock_extractor.extract_pages.return_value = iter([])  # Empty generator
                    mock_extractor_class.return_value = mock_extractor

                    with patch("src.services.background_tasks.TextChunker") as mock_chunker_class:
                        mock_chunker = MagicMock()
                        mock_chunker.chunk_streaming.return_value = iter([])  # No chunks
                        mock_chunker_class.return_value = mock_chunker

                        process_document_task(
                            document_id=1,
                            minio_object_key="documents/2024/01/1_test.pdf",
                            content_type="application/pdf",
                        )

                        assert mock_document.processing_status == "completed"
                        assert mock_document.page_count == 1  # Default
