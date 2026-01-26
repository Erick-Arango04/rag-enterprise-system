"""Document text extraction utilities."""

from io import BytesIO
from typing import Optional, Tuple

import pdfplumber
from docx import Document as DocxDocument

from src.preprocessing.exceptions import (
    CorruptedFileError,
    UnsupportedFormatError,
)


class DocumentExtractor:
    """Extract text content from various document formats."""

    SUPPORTED_CONTENT_TYPES = {
        "application/pdf": "pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
        "text/plain": "text",
        "text/markdown": "text",
    }

    def extract(self, file_data: bytes, content_type: str, filename: str
    ) -> Tuple[Optional[str], Optional[int], Optional[str]]:
        """Extract text from a document.

        Args:
            file_data: The raw file bytes
            content_type: The MIME type of the file
            filename: The original filename

        Returns:
            Tuple of (extracted_text, page_count, error_message)
            - On success: (text, page_count, None)
            - On failure: (None, None, error_message)
        """
        format_type = self.SUPPORTED_CONTENT_TYPES.get(content_type)

        if format_type is None:
            error = UnsupportedFormatError(filename, content_type)
            return None, None, str(error)

        try:
            if format_type == "pdf":
                return self.extract_from_pdf(file_data, filename)
            elif format_type == "docx":
                return self.extract_from_docx(file_data, filename)
            else:
                return self.extract_from_text(file_data, filename)
        except CorruptedFileError as e:
            return None, None, str(e)
        except Exception as e:
            return None, None, f"Extraction failed for {filename}: {str(e)}"

    def extract_from_pdf(
        self, file_data: bytes, filename: str
    ) -> Tuple[Optional[str], Optional[int], Optional[str]]:
        """Extract text from a PDF file using pdfplumber.

        Args:
            file_data: The raw PDF bytes
            filename: The original filename

        Returns:
            Tuple of (extracted_text, page_count, error_message)
        """
        try:
            with pdfplumber.open(BytesIO(file_data)) as pdf:
                pages = []
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        pages.append(text)

                extracted_text = "\n\n".join(pages)
                page_count = len(pdf.pages)

                return extracted_text, page_count, None
        except Exception as e:
            raise CorruptedFileError(filename, f"Failed to parse PDF: {str(e)}")

    def extract_from_docx(
        self, file_data: bytes, filename: str
    ) -> Tuple[Optional[str], Optional[int], Optional[str]]:
        """Extract text from a DOCX file using python-docx.

        Args:
            file_data: The raw DOCX bytes
            filename: The original filename

        Returns:
            Tuple of (extracted_text, page_count, error_message)
            Note: page_count is estimated based on paragraph count
        """
        try:
            doc = DocxDocument(BytesIO(file_data))
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
            extracted_text = "\n\n".join(paragraphs)

            # DOCX doesn't have native page count, return 1 as default
            page_count = 1

            return extracted_text, page_count, None
        except Exception as e:
            raise CorruptedFileError(filename, f"Failed to parse DOCX: {str(e)}")

    def extract_from_text(
        self, file_data: bytes, filename: str
    ) -> Tuple[Optional[str], Optional[int], Optional[str]]:
        """Extract text from a plain text or markdown file.

        Args:
            file_data: The raw text bytes
            filename: The original filename

        Returns:
            Tuple of (extracted_text, page_count, error_message)
        """
        # Try UTF-8 first, fall back to Latin-1
        try:
            extracted_text = file_data.decode("utf-8")
        except UnicodeDecodeError:
            try:
                extracted_text = file_data.decode("latin-1")
            except UnicodeDecodeError as e:
                raise CorruptedFileError(
                    filename, f"Failed to decode text file: {str(e)}"
                )

        # Text files are considered as 1 page
        page_count = 1

        return extracted_text, page_count, None
