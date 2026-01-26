import pytest
from unittest.mock import MagicMock, patch
from io import BytesIO

from src.preprocessing.extractors import DocumentExtractor
from src.preprocessing.exceptions import CorruptedFileError, UnsupportedFormatError


class TestDocumentExtractor:
    """Unit tests for DocumentExtractor."""

    @pytest.fixture
    def extractor(self):
        """Create a DocumentExtractor instance."""
        return DocumentExtractor()

    # Text/Markdown extraction tests
    def test_extract_text_utf8(self, extractor):
        """Test plain text extraction with UTF-8 encoding."""
        content = "Hello, World!\nThis is a test."
        file_data = content.encode("utf-8")

        text, page_count, error = extractor.extract(
            file_data, "text/plain", "test.txt"
        )

        assert text == content
        assert page_count == 1
        assert error is None

    def test_extract_text_latin1_fallback(self, extractor):
        """Test text extraction falls back to Latin-1 encoding."""
        # Latin-1 specific character (not valid UTF-8 on its own)
        content = "Caf\xe9"
        file_data = content.encode("latin-1")

        text, page_count, error = extractor.extract(
            file_data, "text/plain", "test.txt"
        )

        assert text == content
        assert page_count == 1
        assert error is None

    def test_extract_markdown(self, extractor):
        """Test markdown file extraction."""
        content = "# Header\n\nSome **bold** text."
        file_data = content.encode("utf-8")

        text, page_count, error = extractor.extract(
            file_data, "text/markdown", "test.md"
        )

        assert text == content
        assert page_count == 1
        assert error is None

    # Unsupported format tests
    def test_extract_unsupported_format(self, extractor):
        """Test unsupported content type returns error."""
        text, page_count, error = extractor.extract(
            b"data", "image/png", "test.png"
        )

        assert text is None
        assert page_count is None
        assert "Unsupported format" in error

    # PDF extraction tests
    def test_extract_pdf_success(self, extractor):
        """Test PDF extraction with mocked pdfplumber."""
        with patch("src.preprocessing.extractors.pdfplumber") as mock_pdfplumber:
            mock_page = MagicMock()
            mock_page.extract_text.return_value = "Page 1 content"

            mock_pdf = MagicMock()
            mock_pdf.pages = [mock_page]
            mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
            mock_pdf.__exit__ = MagicMock(return_value=False)

            mock_pdfplumber.open.return_value = mock_pdf

            text, page_count, error = extractor.extract(
                b"%PDF-1.4", "application/pdf", "test.pdf"
            )

            assert text == "Page 1 content"
            assert page_count == 1
            assert error is None

    def test_extract_pdf_multiple_pages(self, extractor):
        """Test PDF extraction with multiple pages."""
        with patch("src.preprocessing.extractors.pdfplumber") as mock_pdfplumber:
            mock_page1 = MagicMock()
            mock_page1.extract_text.return_value = "Page 1"
            mock_page2 = MagicMock()
            mock_page2.extract_text.return_value = "Page 2"

            mock_pdf = MagicMock()
            mock_pdf.pages = [mock_page1, mock_page2]
            mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
            mock_pdf.__exit__ = MagicMock(return_value=False)

            mock_pdfplumber.open.return_value = mock_pdf

            text, page_count, error = extractor.extract(
                b"%PDF-1.4", "application/pdf", "test.pdf"
            )

            assert text == "Page 1\n\nPage 2"
            assert page_count == 2
            assert error is None

    def test_extract_pdf_empty_pages_skipped(self, extractor):
        """Test PDF extraction skips empty pages."""
        with patch("src.preprocessing.extractors.pdfplumber") as mock_pdfplumber:
            mock_page1 = MagicMock()
            mock_page1.extract_text.return_value = "Content"
            mock_page2 = MagicMock()
            mock_page2.extract_text.return_value = None  # Empty page

            mock_pdf = MagicMock()
            mock_pdf.pages = [mock_page1, mock_page2]
            mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
            mock_pdf.__exit__ = MagicMock(return_value=False)

            mock_pdfplumber.open.return_value = mock_pdf

            text, page_count, error = extractor.extract(
                b"%PDF-1.4", "application/pdf", "test.pdf"
            )

            assert text == "Content"
            assert page_count == 2  # Still counts all pages
            assert error is None

    def test_extract_pdf_corrupted(self, extractor):
        """Test corrupted PDF returns error."""
        with patch("src.preprocessing.extractors.pdfplumber") as mock_pdfplumber:
            mock_pdfplumber.open.side_effect = Exception("Invalid PDF")

            text, page_count, error = extractor.extract(
                b"not a pdf", "application/pdf", "corrupted.pdf"
            )

            assert text is None
            assert page_count is None
            assert "Failed to parse PDF" in error

    # DOCX extraction tests
    def test_extract_docx_success(self, extractor):
        """Test DOCX extraction with mocked python-docx."""
        with patch("src.preprocessing.extractors.DocxDocument") as mock_docx:
            mock_para1 = MagicMock()
            mock_para1.text = "First paragraph"
            mock_para2 = MagicMock()
            mock_para2.text = "Second paragraph"

            mock_doc = MagicMock()
            mock_doc.paragraphs = [mock_para1, mock_para2]
            mock_docx.return_value = mock_doc

            text, page_count, error = extractor.extract(
                b"PK\x03\x04", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "test.docx"
            )

            assert text == "First paragraph\n\nSecond paragraph"
            assert page_count == 1
            assert error is None

    def test_extract_docx_skips_empty_paragraphs(self, extractor):
        """Test DOCX extraction skips empty paragraphs."""
        with patch("src.preprocessing.extractors.DocxDocument") as mock_docx:
            mock_para1 = MagicMock()
            mock_para1.text = "Content"
            mock_para2 = MagicMock()
            mock_para2.text = "   "  # Whitespace only

            mock_doc = MagicMock()
            mock_doc.paragraphs = [mock_para1, mock_para2]
            mock_docx.return_value = mock_doc

            text, page_count, error = extractor.extract(
                b"PK\x03\x04", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "test.docx"
            )

            assert text == "Content"
            assert error is None

    def test_extract_docx_corrupted(self, extractor):
        """Test corrupted DOCX returns error."""
        with patch("src.preprocessing.extractors.DocxDocument") as mock_docx:
            mock_docx.side_effect = Exception("Invalid DOCX")

            text, page_count, error = extractor.extract(
                b"not a docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "corrupted.docx"
            )

            assert text is None
            assert page_count is None
            assert "Failed to parse DOCX" in error

    # Supported content types test
    def test_supported_content_types(self, extractor):
        """Verify all expected content types are supported."""
        expected_types = {
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "text/plain",
            "text/markdown",
        }
        assert set(extractor.SUPPORTED_CONTENT_TYPES.keys()) == expected_types
