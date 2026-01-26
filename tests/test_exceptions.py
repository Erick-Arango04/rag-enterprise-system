import pytest

from src.preprocessing.exceptions import (
    ExtractionError,
    CorruptedFileError,
    UnsupportedFormatError,
)


class TestExtractionExceptions:
    """Unit tests for extraction exception classes."""

    def test_extraction_error_message_format(self):
        """Test ExtractionError formats message correctly."""
        error = ExtractionError("Something went wrong", "test.pdf")

        assert error.message == "Something went wrong"
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
        assert issubclass(ExtractionError, Exception)

    def test_exceptions_can_be_caught_as_base_type(self):
        """Test exceptions can be caught as ExtractionError."""
        with pytest.raises(ExtractionError):
            raise CorruptedFileError("test.pdf")

        with pytest.raises(ExtractionError):
            raise UnsupportedFormatError("test.png", "image/png")
