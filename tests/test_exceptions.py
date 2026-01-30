import pytest

from src.exceptions import (
    RAGSystemError,
    ExtractionError,
    CorruptedFileError,
    UnsupportedFormatError,
    ChunkingError,
    InvalidChunkConfigError,
    StorageError,
    StorageConnectionError,
    FileUploadError,
    FileDownloadError,
    DocumentError,
    DocumentNotFoundError,
    InvalidFileTypeError,
    FileSizeExceededError,
    ProcessingError,
    DocumentProcessingError,
    StatusUpdateError,
)


class TestBaseException:
    """Unit tests for base RAGSystemError."""

    def test_rag_system_error_message(self):
        """Test RAGSystemError stores and formats message."""
        error = RAGSystemError("Something went wrong")

        assert error.message == "Something went wrong"
        assert str(error) == "Something went wrong"

    def test_all_exceptions_inherit_from_base(self):
        """Test all custom exceptions inherit from RAGSystemError."""
        assert issubclass(ExtractionError, RAGSystemError)
        assert issubclass(ChunkingError, RAGSystemError)
        assert issubclass(StorageError, RAGSystemError)
        assert issubclass(DocumentError, RAGSystemError)
        assert issubclass(ProcessingError, RAGSystemError)


class TestExtractionExceptions:
    """Unit tests for extraction exception classes."""

    def test_extraction_error_message_format(self):
        """Test ExtractionError formats message correctly."""
        error = ExtractionError("Something went wrong", "test.pdf")

        assert error.message == "Something went wrong: test.pdf"
        assert error.filename == "test.pdf"
        assert str(error) == "Something went wrong: test.pdf"

    def test_corrupted_file_error_default_message(self):
        """Test CorruptedFileError with default message."""
        error = CorruptedFileError("document.pdf")

        assert error.filename == "document.pdf"
        assert "corrupted or invalid" in str(error).lower()

    def test_corrupted_file_error_custom_message(self):
        """Test CorruptedFileError with custom message."""
        error = CorruptedFileError("document.pdf", "Failed to parse PDF header")

        assert error.filename == "document.pdf"
        assert "Failed to parse PDF header" in str(error)

    def test_unsupported_format_error(self):
        """Test UnsupportedFormatError includes content type."""
        error = UnsupportedFormatError("image.png", "image/png")

        assert error.filename == "image.png"
        assert "image/png" in str(error)
        assert "Unsupported format" in str(error)

    def test_exceptions_inherit_from_base(self):
        """Test exception inheritance hierarchy."""
        assert issubclass(CorruptedFileError, ExtractionError)
        assert issubclass(UnsupportedFormatError, ExtractionError)
        assert issubclass(ExtractionError, RAGSystemError)

    def test_exceptions_can_be_caught_as_base_type(self):
        """Test exceptions can be caught as ExtractionError."""
        with pytest.raises(ExtractionError):
            raise CorruptedFileError("test.pdf")

        with pytest.raises(ExtractionError):
            raise UnsupportedFormatError("test.png", "image/png")


class TestChunkingExceptions:
    """Unit tests for chunking exception classes."""

    def test_invalid_chunk_config_error(self):
        """Test InvalidChunkConfigError includes config values."""
        error = InvalidChunkConfigError(chunk_size=100, chunk_overlap=150)

        assert error.chunk_size == 100
        assert error.chunk_overlap == 150
        assert "150" in str(error)
        assert "100" in str(error)

    def test_chunking_exceptions_inherit_from_base(self):
        """Test chunking exception hierarchy."""
        assert issubclass(InvalidChunkConfigError, ChunkingError)
        assert issubclass(ChunkingError, RAGSystemError)


class TestStorageExceptions:
    """Unit tests for storage exception classes."""

    def test_storage_connection_error(self):
        """Test StorageConnectionError includes endpoint."""
        error = StorageConnectionError("localhost:9000")

        assert error.endpoint == "localhost:9000"
        assert "localhost:9000" in str(error)

    def test_file_upload_error(self):
        """Test FileUploadError includes file and bucket info."""
        error = FileUploadError("test.pdf", "documents", "Connection timeout")

        assert error.filename == "test.pdf"
        assert error.bucket == "documents"
        assert "test.pdf" in str(error)
        assert "documents" in str(error)

    def test_file_download_error(self):
        """Test FileDownloadError includes object key and bucket."""
        error = FileDownloadError("docs/test.pdf", "documents", "Object not found")

        assert error.object_key == "docs/test.pdf"
        assert error.bucket == "documents"
        assert "docs/test.pdf" in str(error)

    def test_storage_exceptions_inherit_from_base(self):
        """Test storage exception hierarchy."""
        assert issubclass(StorageConnectionError, StorageError)
        assert issubclass(FileUploadError, StorageError)
        assert issubclass(FileDownloadError, StorageError)
        assert issubclass(StorageError, RAGSystemError)


class TestDocumentExceptions:
    """Unit tests for document exception classes."""

    def test_document_not_found_error(self):
        """Test DocumentNotFoundError includes document ID."""
        error = DocumentNotFoundError(42)

        assert error.document_id == 42
        assert "42" in str(error)

    def test_invalid_file_type_error(self):
        """Test InvalidFileTypeError includes file details."""
        error = InvalidFileTypeError(
            "image.png", "image/png", ["application/pdf", "text/plain"]
        )

        assert error.filename == "image.png"
        assert error.content_type == "image/png"
        assert "image/png" in str(error)
        assert "application/pdf" in str(error)

    def test_file_size_exceeded_error(self):
        """Test FileSizeExceededError includes size info."""
        error = FileSizeExceededError("large.pdf", 100_000_000, 50_000_000)

        assert error.filename == "large.pdf"
        assert error.file_size == 100_000_000
        assert error.max_size == 50_000_000
        assert "100000000" in str(error)

    def test_document_exceptions_inherit_from_base(self):
        """Test document exception hierarchy."""
        assert issubclass(DocumentNotFoundError, DocumentError)
        assert issubclass(InvalidFileTypeError, DocumentError)
        assert issubclass(FileSizeExceededError, DocumentError)
        assert issubclass(DocumentError, RAGSystemError)


class TestProcessingExceptions:
    """Unit tests for processing exception classes."""

    def test_document_processing_error(self):
        """Test DocumentProcessingError includes context."""
        error = DocumentProcessingError(1, "extraction", "PDF parsing failed")

        assert error.document_id == 1
        assert error.stage == "extraction"
        assert "extraction" in str(error)
        assert "PDF parsing failed" in str(error)

    def test_status_update_error(self):
        """Test StatusUpdateError includes status info."""
        error = StatusUpdateError(1, "completed", "Database connection lost")

        assert error.document_id == 1
        assert error.target_status == "completed"
        assert "completed" in str(error)

    def test_processing_exceptions_inherit_from_base(self):
        """Test processing exception hierarchy."""
        assert issubclass(DocumentProcessingError, ProcessingError)
        assert issubclass(StatusUpdateError, ProcessingError)
        assert issubclass(ProcessingError, RAGSystemError)
