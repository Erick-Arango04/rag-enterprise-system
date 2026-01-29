"""Document text chunking utilities."""

import re
from dataclasses import dataclass, field
from typing import List, Optional


# Chunking configuration
CHUNKING_CONFIG = {
    "chunk_size": 1000,        # Characters per chunk
    "chunk_overlap": 200,      # Overlap between chunks
    "separator": "\n\n",       # Paragraph separator
}

# Decorator that automatically generates common methods for classes that mainly store data.
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


class TextChunker:
    """Split text into overlapping chunks for embedding generation.

    The chunker splits text on paragraph boundaries first, then accumulates
    segments into chunks up to the configured size. Consecutive chunks
    overlap to preserve context across chunk boundaries.
    """

    def __init__(
        self,
        chunk_size: int = CHUNKING_CONFIG["chunk_size"],
        chunk_overlap: int = CHUNKING_CONFIG["chunk_overlap"],
        separator: str = CHUNKING_CONFIG["separator"],
    ):
        """Initialize the chunker with configuration.

        Args:
            chunk_size: Maximum characters per chunk
            chunk_overlap: Number of characters to overlap between chunks
            separator: String to split text on (default: paragraph boundary)
        """
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be less than chunk_size")

        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separator = separator

    def chunk(self, text: str) -> List[TextChunk]:
        """Split text into overlapping chunks.

        Args:
            text: The text to split into chunks

        Returns:
            List of TextChunk objects with content and position info
        """
        if not text or not text.strip():
            return []

        # Split on separator to get segments
        segments = text.split(self.separator)

        chunks: List[TextChunk] = []
        current_chunk = ""
        current_start = 0
        chunk_index = 0

        for i, segment in enumerate(segments):
            segment = segment.strip()
            if not segment:
                continue

            # Check if adding this segment would exceed chunk_size
            if current_chunk:
                potential = current_chunk + self.separator + segment
            else:
                potential = segment

            if len(potential) <= self.chunk_size:
                # Add segment to current chunk
                current_chunk = potential
            else:
                # Current chunk is full, save it
                if current_chunk:
                    chunk_end = current_start + len(current_chunk)
                    chunks.append(
                        TextChunk(
                            content=current_chunk,
                            chunk_index=chunk_index,
                            start_char=current_start,
                            end_char=chunk_end,
                        )
                    )
                    chunk_index += 1

                    # Calculate overlap start position
                    overlap_text = self._get_overlap_text(current_chunk)
                    current_start = chunk_end - len(overlap_text)
                    current_chunk = overlap_text + self.separator + segment if overlap_text else segment
                else:
                    current_chunk = segment

                # If single segment is too large, split it
                if len(current_chunk) > self.chunk_size:
                    sub_chunks = self._split_large_segment(
                        current_chunk, current_start, chunk_index
                    )
                    chunks.extend(sub_chunks[:-1])
                    chunk_index += len(sub_chunks) - 1

                    # Keep the last sub-chunk as current
                    last = sub_chunks[-1]
                    current_chunk = last.content
                    current_start = last.start_char

        # Add remaining content as final chunk
        if current_chunk:
            chunk_end = current_start + len(current_chunk)
            chunks.append(
                TextChunk(
                    content=current_chunk,
                    chunk_index=chunk_index,
                    start_char=current_start,
                    end_char=chunk_end,
                )
            )

        return chunks

    def _get_overlap_text(self, text: str) -> str:
        """Extract overlap text from the end of a chunk.

        Attempts to break at word boundaries within the overlap region.

        Args:
            text: The chunk text to extract overlap from

        Returns:
            The overlap text (up to chunk_overlap characters)
        """
        if len(text) <= self.chunk_overlap:
            return text

        overlap = text[-self.chunk_overlap:]

        # Try to break at a word boundary
        space_idx = overlap.find(" ")
        if space_idx > 0:
            overlap = overlap[space_idx + 1:]

        return overlap

    def _split_large_segment(
        self, segment: str, start_pos: int, start_index: int
    ) -> List[TextChunk]:
        """Split a segment that exceeds chunk_size.

        Strategy: Try sentences first, then word boundaries (iterative).

        Args:
            segment: The large segment to split
            start_pos: Starting character position in original text
            start_index: Starting chunk index

        Returns:
            List of TextChunk objects
        """
        # First, try to split by sentences
        sentences = self._split_into_sentences(segment)

        # If only one sentence (or no sentence breaks), fall back to word splitting
        if len(sentences) <= 1:
            return self._split_by_words(segment, start_pos, start_index)

        # Iteratively accumulate sentences into chunks
        chunks: List[TextChunk] = []
        chunk_index = start_index
        current_text = ""
        current_start = start_pos

        for sentence in sentences:
            # Check if sentence fits in current chunk
            if not current_text:
                current_text = sentence
            elif len(current_text) + 1 + len(sentence) <= self.chunk_size:
                current_text += " " + sentence
            else:
                # Save current chunk
                chunks.append(
                    TextChunk(
                        content=current_text,
                        chunk_index=chunk_index,
                        start_char=current_start,
                        end_char=current_start + len(current_text),
                    )
                )
                chunk_index += 1

                # Start new chunk with overlap
                overlap = self._get_overlap_text(current_text)
                current_start = current_start + len(current_text) - len(overlap)
                current_text = overlap + " " + sentence if overlap else sentence

            # If single sentence is still too large, split by words
            if len(current_text) > self.chunk_size:
                word_chunks = self._split_by_words(current_text, current_start, chunk_index)
                if len(word_chunks) > 1:
                    chunks.extend(word_chunks[:-1])
                    chunk_index += len(word_chunks) - 1
                    last = word_chunks[-1]
                    current_text = last.content
                    current_start = last.start_char

        # Don't forget remaining text
        if current_text:
            chunks.append(
                TextChunk(
                    content=current_text,
                    chunk_index=chunk_index,
                    start_char=current_start,
                    end_char=current_start + len(current_text),
                )
            )

        return chunks

    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences using common delimiters.

        Args:
            text: The text to split into sentences

        Returns:
            List of sentence strings
        """
        # Split on . ! ? followed by space or end of string
        sentence_pattern = r'(?<=[.!?])\s+'
        sentences = re.split(sentence_pattern, text)
        return [s.strip() for s in sentences if s.strip()]

    def _split_by_words(
        self, segment: str, start_pos: int, start_index: int
    ) -> List[TextChunk]:
        """Split a segment at word boundaries when it exceeds chunk_size.

        Args:
            segment: The large segment to split
            start_pos: Starting character position in original text
            start_index: Starting chunk index

        Returns:
            List of TextChunk objects
        """
        chunks: List[TextChunk] = []
        current_pos = 0
        chunk_index = start_index

        while current_pos < len(segment):
            # Determine end position for this chunk
            end_pos = min(current_pos + self.chunk_size, len(segment))

            # If not at end, try to break at word boundary
            if end_pos < len(segment):
                # Look for last space within chunk_size
                last_space = segment.rfind(" ", current_pos, end_pos)
                if last_space > current_pos:
                    end_pos = last_space

            chunk_content = segment[current_pos:end_pos].strip()

            if chunk_content:
                chunks.append(
                    TextChunk(
                        content=chunk_content,
                        chunk_index=chunk_index,
                        start_char=start_pos + current_pos,
                        end_char=start_pos + end_pos,
                    )
                )
                chunk_index += 1

            # Move position, applying overlap
            if end_pos < len(segment):
                current_pos = end_pos - self.chunk_overlap
            else:
                break

        return chunks

    def chunk_to_db_records(
        self,
        text: str,
        document_id: int,
        extra_metadata: Optional[dict] = None,
    ) -> List[dict]:
        """Chunk text and return database-ready records.

        Args:
            text: The text to chunk
            document_id: The ID of the parent document
            extra_metadata: Optional additional metadata to include

        Returns:
            List of dicts ready for document_chunks table insertion
        """
        chunks = self.chunk(text)
        return [c.to_db_record(document_id, extra_metadata) for c in chunks]
