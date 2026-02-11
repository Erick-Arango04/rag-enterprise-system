"""Document text extraction utilities with generator-based streaming."""

from dataclasses import dataclass
from io import BytesIO
from typing import Generator

import pdfplumber
from docx import Document as DocxDocument

from src.exceptions import (
    CorruptedFileError,
    UnsupportedFormatError,
)


# Configuration for text file chunking
TEXT_CHUNK_SIZE = 10 * 1024  # 10KB chunks for text files
DOCX_PARAGRAPHS_PER_BATCH = 10  # Group paragraphs into batches


@dataclass
class PageContent:
    """Represents extracted content from a single page or section.

    Attributes:
        text: The extracted text content
        page_number: Current page/section number (1-based)
        total_pages: Total number of pages/sections in the document
        is_last: Whether this is the last page/section
    """

    text: str
    page_number: int
    total_pages: int
    is_last: bool = False


class DocumentExtractor:
    """Extract text content from various document formats using generators.

    This extractor yields content page-by-page (or in batches) for memory
    efficiency, allowing large documents to be processed without loading
    the entire content into memory.
    """

    SUPPORTED_CONTENT_TYPES = {
        "application/pdf": "pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
        "text/plain": "text",
        "text/markdown": "text",
    }

    def extract_pages(
        self, file_data: bytes, content_type: str, filename: str
    ) -> Generator[PageContent, None, None]:
        """Extract text from a document, yielding page by page.

        Args:
            file_data: The raw file bytes
            content_type: The MIME type of the file
            filename: The original filename

        Yields:
            PageContent objects containing text and metadata for each page

        Raises:
            UnsupportedFormatError: If the content type is not supported
            CorruptedFileError: If the file cannot be parsed
        """
        format_type = self.SUPPORTED_CONTENT_TYPES.get(content_type)

        if format_type is None:
            raise UnsupportedFormatError(filename, content_type)

        if format_type == "pdf":
            yield from self._extract_pdf_pages(file_data, filename)
        elif format_type == "docx":
            yield from self._extract_docx_pages(file_data, filename)
        else:
            yield from self._extract_text_pages(file_data, filename)

    def _extract_pdf_pages(
        self, file_data: bytes, filename: str
    ) -> Generator[PageContent, None, None]:
        """Extract text from a PDF file, yielding one page at a time.

        Args:
            file_data: The raw PDF bytes
            filename: The original filename

        Yields:
            PageContent for each page in the PDF
        """
        try:
            with pdfplumber.open(BytesIO(file_data)) as pdf:
                total_pages = len(pdf.pages)

                for i, page in enumerate(pdf.pages):
                    text = page.extract_text() or ""
                    page_number = i + 1
                    is_last = page_number == total_pages

                    if text.strip():
                        yield PageContent(
                            text=text,
                            page_number=page_number,
                            total_pages=total_pages,
                            is_last=is_last,
                        )
                    elif is_last and page_number == 1:
                        # Empty single-page PDF
                        yield PageContent(
                            text="",
                            page_number=1,
                            total_pages=1,
                            is_last=True,
                        )
        except Exception as e:
            raise CorruptedFileError(filename, f"Failed to parse PDF: {e}")

    def _extract_docx_pages(
        self, file_data: bytes, filename: str
    ) -> Generator[PageContent, None, None]:
        """Extract text from a DOCX file, yielding batches of paragraphs.

        DOCX files don't have native page boundaries, so we batch paragraphs
        into logical sections.

        Args:
            file_data: The raw DOCX bytes
            filename: The original filename

        Yields:
            PageContent for each batch of paragraphs
        """
        try:
            doc = DocxDocument(BytesIO(file_data))
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]

            if not paragraphs:
                yield PageContent(
                    text="",
                    page_number=1,
                    total_pages=1,
                    is_last=True,
                )
                return

            # Calculate total batches
            total_batches = (len(paragraphs) + DOCX_PARAGRAPHS_PER_BATCH - 1) // DOCX_PARAGRAPHS_PER_BATCH

            for batch_num in range(total_batches):
                start_idx = batch_num * DOCX_PARAGRAPHS_PER_BATCH
                end_idx = min(start_idx + DOCX_PARAGRAPHS_PER_BATCH, len(paragraphs))
                batch_paragraphs = paragraphs[start_idx:end_idx]

                batch_text = "\n\n".join(batch_paragraphs)
                page_number = batch_num + 1
                is_last = page_number == total_batches

                yield PageContent(
                    text=batch_text,
                    page_number=page_number,
                    total_pages=total_batches,
                    is_last=is_last,
                )
        except Exception as e:
            raise CorruptedFileError(filename, f"Failed to parse DOCX: {e}")

    def _extract_text_pages(
        self, file_data: bytes, filename: str
    ) -> Generator[PageContent, None, None]:
        """Extract text from a plain text or markdown file in chunks.

        Args:
            file_data: The raw text bytes
            filename: The original filename

        Yields:
            PageContent for each chunk of text
        """
        # Decode the text
        try:
            text = file_data.decode("utf-8")
        except UnicodeDecodeError:
            try:
                text = file_data.decode("latin-1")
            except UnicodeDecodeError as e:
                raise CorruptedFileError(filename, f"Failed to decode text file: {e}")

        if not text.strip():
            yield PageContent(
                text="",
                page_number=1,
                total_pages=1,
                is_last=True,
            )
            return

        # Calculate total chunks
        total_chunks = (len(text) + TEXT_CHUNK_SIZE - 1) // TEXT_CHUNK_SIZE

        for chunk_num in range(total_chunks):
            start_idx = chunk_num * TEXT_CHUNK_SIZE
            end_idx = min(start_idx + TEXT_CHUNK_SIZE, len(text))

            # Try to break at a word boundary for cleaner chunks
            if end_idx < len(text):
                # Look for last space within the chunk
                last_space = text.rfind(" ", start_idx, end_idx)
                if last_space > start_idx:
                    end_idx = last_space

            chunk_text = text[start_idx:end_idx].strip()
            page_number = chunk_num + 1
            is_last = end_idx >= len(text) or page_number == total_chunks

            if chunk_text:
                yield PageContent(
                    text=chunk_text,
                    page_number=page_number,
                    total_pages=total_chunks,
                    is_last=is_last,
                )
