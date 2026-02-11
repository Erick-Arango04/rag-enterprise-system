"""Chunk-related data models."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class TextChunk:
    """Represents a chunk of text from a document.

    Attributes:
        content: The chunk text content
        chunk_index: Sequential index (0-based)
        start_char: Starting character position in original text
        end_char: Ending character position in original text
        metadata: Optional dictionary for additional info
    """

    content: str
    chunk_index: int
    start_char: int
    end_char: int
    metadata: Optional[dict] = field(default=None)

    def to_db_record(self, document_id: int, extra_metadata: Optional[dict] = None) -> dict:
        """Convert to database-ready dict for document_chunks table.

        Args:
            document_id: The ID of the parent document
            extra_metadata: Optional additional metadata to include

        Returns:
            Dict with keys: document_id, chunk_index, content, metadata
        """
        return {
            "document_id": document_id,
            "chunk_index": self.chunk_index,
            "content": self.content,
            "metadata": {
                "start_char": self.start_char,
                "end_char": self.end_char,
                **(self.metadata or {}),
                **(extra_metadata or {}),
            },
        }
