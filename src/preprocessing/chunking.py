"""Document text chunking utilities for RAG pipelines.

This module provides text chunking functionality optimized for embedding generation
and semantic search. It splits documents into overlapping chunks while preserving
semantic boundaries (paragraphs, sentences, words).

Key components:
    - TextChunker: Main class for splitting text into chunks
    - CHUNKING_CONFIG: Default configuration values

Typical usage:
    >>> from src.preprocessing.chunking import TextChunker
    >>> chunker = TextChunker(chunk_size=1000, chunk_overlap=200)
    >>> chunks = chunker.chunk("Your document text here...")
"""

import re
from dataclasses import dataclass
from typing import Generator, List, Optional

from src.exceptions import InvalidChunkConfigError
from src.models.chunk import TextChunk
from src.preprocessing.extractors import PageContent


# Chunking configuration
CHUNKING_CONFIG = {
    "chunk_size": 1000,        # Characters per chunk
    "chunk_overlap": 200,      # Overlap between chunks
    "separator": "\n\n",       # Paragraph separator
}


@dataclass
class _ChunkingState:
    """Internal state for segment processing.

    Tracks the current chunk being built and position information
    during chunking operations.
    """

    current_chunk: str = ""
    current_start: int = 0
    chunk_index: int = 0

class TextChunker:
    """Split text into overlapping chunks for embedding generation.

    This class implements a hierarchical chunking strategy optimized for RAG
    (Retrieval-Augmented Generation) pipelines. It produces chunks suitable
    for embedding generation while preserving semantic coherence.

    Chunking Algorithm:
        1. Split text on paragraph boundaries (separator)
        2. Accumulate paragraphs until chunk_size is reached
        3. When a chunk is full, emit it and start a new one with overlap
        4. For oversized paragraphs: split by sentences first, then by words
        5. Overlap ensures context continuity across chunk boundaries

    Attributes:
        chunk_size: Maximum characters per chunk (default: 1000)
        chunk_overlap: Characters to repeat between consecutive chunks (default: 200)
        separator: String used to split text into segments (default: "\\n\\n")
    Raises:
        InvalidChunkConfigError: If chunk_overlap >= chunk_size
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
            raise InvalidChunkConfigError(chunk_size, chunk_overlap)

        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separator = separator

    def chunk(self, text: str) -> List[TextChunk]:
        """Split text into overlapping chunks.

        Processes the entire text in memory and returns all chunks at once.
        For large documents, consider using chunk_streaming() instead.

        Args:
            text: The text to split into chunks. Empty or whitespace-only
                text returns an empty list.

        Returns:
            List of TextChunk objects ordered by chunk_index, each containing:
                - content: The chunk text
                - chunk_index: Sequential index (0-based)
                - start_char: Starting position in original text
                - end_char: Ending position in original text

        Example:
            >>> chunker = TextChunker(chunk_size=50, chunk_overlap=10)
            >>> chunks = chunker.chunk("Hello world.\\n\\nThis is a test.")
            >>> len(chunks)
            1
            >>> chunks[0].content
            'Hello world.\\n\\nThis is a test.'
        """
        if not text or not text.strip():
            return []

        segments = text.split(self.separator)
        state = _ChunkingState()

        chunks = list(self._process_segments(segments, state))

        # Add remaining content as final chunk
        if state.current_chunk:
            chunks.append(
                TextChunk(
                    content=state.current_chunk,
                    chunk_index=state.chunk_index,
                    start_char=state.current_start,
                    end_char=state.current_start + len(state.current_chunk),
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

    def chunk_streaming(
        self,
        pages: Generator[PageContent, None, None],
    ) -> Generator[TextChunk, None, None]:
        """Chunk text from a page generator, yielding chunks as produced.

        This method processes pages one at a time, maintaining overlap context
        across page boundaries. Ideal for memory-efficient processing of large
        documents where loading the entire text into memory is impractical.

        The streaming approach:
            1. Processes one page at a time from the generator
            2. Carries incomplete chunks across page boundaries
            3. Yields complete chunks as soon as they're ready
            4. Automatically includes page_number in chunk metadata

        Args:
            pages: Generator yielding PageContent objects. Each PageContent must have:
                - text: The page's text content
                - page_number: 1-based page number
                - is_last: Boolean indicating if this is the final page

        Yields:
            TextChunk objects as they are completed. Each chunk includes
            metadata with 'page_number' indicating where the chunk originated.

        Note:
            Chunks may span page boundaries. The page_number in metadata
            reflects the page where the chunk was finalized, not necessarily
            where all its content originated.

        Example:
            >>> def extract_pages(pdf_path):
            ...     for i, page in enumerate(pdf_pages):
            ...         yield PageContent(
            ...             text=page.extract_text(),
            ...             page_number=i + 1,
            ...             is_last=(i == len(pdf_pages) - 1)
            ...         )
            >>> chunker = TextChunker()
            >>> for chunk in chunker.chunk_streaming(extract_pages("doc.pdf")):
            ...     save_to_database(chunk)
        """
        state = _ChunkingState()
        leftover_text = ""

        for page in pages:
            # Combine leftover with current page text
            if leftover_text:
                text_to_process = leftover_text + self.separator + page.text
            else:
                text_to_process = page.text

            if not text_to_process.strip():
                continue

            segments = text_to_process.split(self.separator)
            metadata = {"page_number": page.page_number}

            # Process segments and yield completed chunks
            for chunk in self._process_segments(segments, state, metadata):
                yield chunk

            # At end of page, decide what to carry over
            if page.is_last:
                # Final page - yield remaining content
                if state.current_chunk:
                    yield TextChunk(
                        content=state.current_chunk,
                        chunk_index=state.chunk_index,
                        start_char=state.current_start,
                        end_char=state.current_start + len(state.current_chunk),
                        metadata=metadata,
                    )
                leftover_text = ""
            else:
                # More pages coming - carry over current chunk for context
                leftover_text = state.current_chunk
                # Update start position for next page, accounting for overlap
                if state.current_chunk:
                    overlap_len = len(self._get_overlap_text(state.current_chunk))
                    state.current_start = (
                        state.current_start + len(state.current_chunk) - overlap_len
                    )
                # Reset current_chunk since leftover will be prepended to next page
                state.current_chunk = ""

    def _process_segments(
        self,
        segments: List[str],
        state: _ChunkingState,
        base_metadata: Optional[dict] = None,
    ) -> Generator[TextChunk, None, None]:
        """Process segments into chunks, yielding as they complete.

        This is the core chunking logic used by both chunk() and chunk_streaming().
        Mutates state in-place to track position across calls.

        Args:
            segments: List of text segments to process
            state: Mutable state tracking current chunk and position
            base_metadata: Optional metadata to attach to yielded chunks

        Yields:
            TextChunk objects as they are completed
        """
        for segment in segments:
            segment = segment.strip()
            if not segment:
                continue

            # Check if adding this segment would exceed chunk_size
            if state.current_chunk:
                potential = state.current_chunk + self.separator + segment
            else:
                potential = segment


            if len(potential) <= self.chunk_size:
                state.current_chunk = potential
            else:
                # Current chunk is full, yield it
                if state.current_chunk:
                    chunk_end = state.current_start + len(state.current_chunk)
                    yield TextChunk(
                        content=state.current_chunk,
                        chunk_index=state.chunk_index,
                        start_char=state.current_start,
                        end_char=chunk_end,
                        metadata=base_metadata.copy() if base_metadata else None,
                    )
                    state.chunk_index += 1

                    # Calculate overlap for next chunk
                    overlap_text = self._get_overlap_text(state.current_chunk)
                    state.current_start = chunk_end - len(overlap_text)
                    state.current_chunk = (
                        overlap_text + self.separator + segment if overlap_text else segment
                    )
                else:
                    state.current_chunk = segment

                # If single segment is too large, split and yield
                if len(state.current_chunk) > self.chunk_size:
                    sub_chunks = self._split_large_segment(
                        state.current_chunk, state.current_start, state.chunk_index
                    )
                    # Yield all but the last sub-chunk
                    for sub_chunk in sub_chunks[:-1]:
                        if base_metadata:
                            sub_chunk.metadata = base_metadata.copy()
                        yield sub_chunk
                    state.chunk_index += len(sub_chunks) - 1

                    # Keep the last sub-chunk as current
                    last = sub_chunks[-1]
                    state.current_chunk = last.content
                    state.current_start = last.start_char

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

        Convenience method that chunks text and converts each chunk to a
        dictionary format suitable for bulk insertion into the document_chunks
        table.

        Args:
            text: The text to chunk
            document_id: The ID of the parent document in the documents table
            extra_metadata: Optional additional metadata to merge into each
                chunk's metadata (e.g., {"filename": "doc.pdf"})

        Returns:
            List of dicts with keys: document_id, chunk_index, content, metadata.
            The metadata dict includes start_char, end_char, and any extra_metadata.

        Example:
            >>> chunker = TextChunker()
            >>> records = chunker.chunk_to_db_records(
            ...     text="Document content...",
            ...     document_id=123,
            ...     extra_metadata={"source": "upload"}
            ... )
            >>> # Bulk insert with SQLAlchemy
            >>> session.execute(insert(DocumentChunk), records)
        """
        chunks = self.chunk(text)
        return [c.to_db_record(document_id, extra_metadata) for c in chunks]
