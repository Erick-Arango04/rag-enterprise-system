import pytest
from unittest.mock import MagicMock, patch

from src.exceptions import CorruptedFileError, UnsupportedFormatError
from src.preprocessing.extractors import DocumentExtractor, PageContent


class TestDocumentExtractor:
    """Unit tests for DocumentExtractor with generator-based extraction."""

    @pytest.fixture
    def extractor(self):
        """Create a DocumentExtractor instance."""
        return DocumentExtractor()

    # Text/Markdown extraction tests
    def test_extract_pages_text_utf8(self, extractor):
        """Test plain text extraction with UTF-8 encoding."""
        content = "Hello, World!\nThis is a test."
        file_data = content.encode("utf-8")

        pages = list(extractor.extract_pages(file_data, "text/plain", "test.txt"))

        assert len(pages) == 1
        assert pages[0].text == content
        assert pages[0].page_number == 1
        assert pages[0].is_last is True

    def test_extract_pages_text_latin1_fallback(self, extractor):
        """Test text extraction falls back to Latin-1 encoding."""
        content = "Café"
        file_data = content.encode("latin-1")

        pages = list(extractor.extract_pages(file_data, "text/plain", "test.txt"))

        assert len(pages) == 1
        assert pages[0].text == content

    def test_extract_pages_markdown(self, extractor):
        """Test markdown file extraction."""
        content = "# Header\n\nSome **bold** text."
        file_data = content.encode("utf-8")

        pages = list(extractor.extract_pages(file_data, "text/markdown", "test.md"))

        assert len(pages) == 1
        assert pages[0].text == content

    def test_extract_pages_large_text_yields_multiple_chunks(self, extractor):
        """Test that large text files are split into multiple chunks."""
        # Create content larger than TEXT_CHUNK_SIZE (10KB)
        content = "A" * 25000  # 25KB of text
        file_data = content.encode("utf-8")

        pages = list(extractor.extract_pages(file_data, "text/plain", "large.txt"))

        assert len(pages) >= 2
        assert pages[0].page_number == 1
        assert pages[-1].is_last is True
        # Verify all content is captured
        total_text = "".join(p.text for p in pages)
        assert len(total_text) == len(content)

    def test_extract_pages_empty_text(self, extractor):
        """Test empty text file yields single empty page."""
        file_data = b""

        pages = list(extractor.extract_pages(file_data, "text/plain", "empty.txt"))

        assert len(pages) == 1
        assert pages[0].text == ""
        assert pages[0].is_last is True

    # Unsupported format tests
    def test_extract_pages_unsupported_format(self, extractor):
        """Test unsupported content type raises exception."""
        with pytest.raises(UnsupportedFormatError):
            list(extractor.extract_pages(b"data", "image/png", "test.png"))

    # PDF extraction tests
    def test_extract_pages_pdf_success(self, extractor):
        """Test PDF extraction with mocked pdfplumber."""
        with patch("src.preprocessing.extractors.pdfplumber") as mock_pdfplumber:
            mock_page = MagicMock()
            mock_page.extract_text.return_value = "Page 1 content"

            mock_pdf = MagicMock()
            mock_pdf.pages = [mock_page]
            mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
            mock_pdf.__exit__ = MagicMock(return_value=False)

            mock_pdfplumber.open.return_value = mock_pdf

            pages = list(extractor.extract_pages(
                b"%PDF-1.4", "application/pdf", "test.pdf"
            ))

            assert len(pages) == 1
            assert pages[0].text == "Page 1 content"
            assert pages[0].page_number == 1
            assert pages[0].total_pages == 1
            assert pages[0].is_last is True

    def test_extract_pages_pdf_multiple_pages(self, extractor):
        """Test PDF extraction yields one PageContent per page."""
        with patch("src.preprocessing.extractors.pdfplumber") as mock_pdfplumber:
            mock_page1 = MagicMock()
            mock_page1.extract_text.return_value = "Page 1"
            mock_page2 = MagicMock()
            mock_page2.extract_text.return_value = "Page 2"
            mock_page3 = MagicMock()
            mock_page3.extract_text.return_value = "Page 3"

            mock_pdf = MagicMock()
            mock_pdf.pages = [mock_page1, mock_page2, mock_page3]
            mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
            mock_pdf.__exit__ = MagicMock(return_value=False)

            mock_pdfplumber.open.return_value = mock_pdf

            pages = list(extractor.extract_pages(
                b"%PDF-1.4", "application/pdf", "test.pdf"
            ))

            assert len(pages) == 3
            assert pages[0].page_number == 1
            assert pages[0].text == "Page 1"
            assert pages[0].is_last is False
            assert pages[1].page_number == 2
            assert pages[1].text == "Page 2"
            assert pages[2].page_number == 3
            assert pages[2].is_last is True
            assert all(p.total_pages == 3 for p in pages)

    def test_extract_pages_pdf_empty_pages_skipped(self, extractor):
        """Test PDF extraction skips empty pages but includes total count."""
        with patch("src.preprocessing.extractors.pdfplumber") as mock_pdfplumber:
            mock_page1 = MagicMock()
            mock_page1.extract_text.return_value = "Content"
            mock_page2 = MagicMock()
            mock_page2.extract_text.return_value = None  # Empty page
            mock_page3 = MagicMock()
            mock_page3.extract_text.return_value = ""  # Whitespace only

            mock_pdf = MagicMock()
            mock_pdf.pages = [mock_page1, mock_page2, mock_page3]
            mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
            mock_pdf.__exit__ = MagicMock(return_value=False)

            mock_pdfplumber.open.return_value = mock_pdf

            pages = list(extractor.extract_pages(
                b"%PDF-1.4", "application/pdf", "test.pdf"
            ))

            # Only page with content is yielded
            assert len(pages) == 1
            assert pages[0].text == "Content"
            assert pages[0].total_pages == 3

    def test_extract_pages_pdf_corrupted(self, extractor):
        """Test corrupted PDF raises CorruptedFileError."""
        with patch("src.preprocessing.extractors.pdfplumber") as mock_pdfplumber:
            mock_pdfplumber.open.side_effect = Exception("Invalid PDF")

            with pytest.raises(CorruptedFileError) as exc_info:
                list(extractor.extract_pages(
                    b"not a pdf", "application/pdf", "corrupted.pdf"
                ))

            assert "Failed to parse PDF" in str(exc_info.value)

    # DOCX extraction tests
    def test_extract_pages_docx_success(self, extractor):
        """Test DOCX extraction with mocked python-docx."""
        with patch("src.preprocessing.extractors.DocxDocument") as mock_docx:
            mock_para1 = MagicMock()
            mock_para1.text = "First paragraph"
            mock_para2 = MagicMock()
            mock_para2.text = "Second paragraph"

            mock_doc = MagicMock()
            mock_doc.paragraphs = [mock_para1, mock_para2]
            mock_docx.return_value = mock_doc

            pages = list(extractor.extract_pages(
                b"PK\x03\x04",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "test.docx"
            ))

            assert len(pages) == 1
            assert "First paragraph" in pages[0].text
            assert "Second paragraph" in pages[0].text

    def test_extract_pages_docx_many_paragraphs_batched(self, extractor):
        """Test DOCX with many paragraphs yields multiple batches."""
        with patch("src.preprocessing.extractors.DocxDocument") as mock_docx:
            # Create 25 paragraphs (should yield 3 batches with 10 paragraphs each)
            paragraphs = []
            for i in range(25):
                mock_para = MagicMock()
                mock_para.text = f"Paragraph {i}"
                paragraphs.append(mock_para)

            mock_doc = MagicMock()
            mock_doc.paragraphs = paragraphs
            mock_docx.return_value = mock_doc

            pages = list(extractor.extract_pages(
                b"PK\x03\x04",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "test.docx"
            ))

            assert len(pages) == 3
            assert pages[0].page_number == 1
            assert pages[2].page_number == 3
            assert pages[2].is_last is True

    def test_extract_pages_docx_skips_empty_paragraphs(self, extractor):
        """Test DOCX extraction skips empty paragraphs."""
        with patch("src.preprocessing.extractors.DocxDocument") as mock_docx:
            mock_para1 = MagicMock()
            mock_para1.text = "Content"
            mock_para2 = MagicMock()
            mock_para2.text = "   "  # Whitespace only

            mock_doc = MagicMock()
            mock_doc.paragraphs = [mock_para1, mock_para2]
            mock_docx.return_value = mock_doc

            pages = list(extractor.extract_pages(
                b"PK\x03\x04",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "test.docx"
            ))

            assert len(pages) == 1
            assert pages[0].text == "Content"

    def test_extract_pages_docx_corrupted(self, extractor):
        """Test corrupted DOCX raises CorruptedFileError."""
        with patch("src.preprocessing.extractors.DocxDocument") as mock_docx:
            mock_docx.side_effect = Exception("Invalid DOCX")

            with pytest.raises(CorruptedFileError) as exc_info:
                list(extractor.extract_pages(
                    b"not a docx",
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    "corrupted.docx"
                ))

            assert "Failed to parse DOCX" in str(exc_info.value)

    # PageContent dataclass tests
    def test_page_content_dataclass(self):
        """Test PageContent dataclass attributes."""
        page = PageContent(
            text="Sample text",
            page_number=1,
            total_pages=5,
            is_last=False,
        )

        assert page.text == "Sample text"
        assert page.page_number == 1
        assert page.total_pages == 5
        assert page.is_last is False

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

    # Generator behavior tests
    def test_extract_pages_is_generator(self, extractor):
        """Test that extract_pages returns a generator."""
        content = "Hello, World!"
        file_data = content.encode("utf-8")

        result = extractor.extract_pages(file_data, "text/plain", "test.txt")

        # Should be a generator, not a list
        import types
        assert isinstance(result, types.GeneratorType)
