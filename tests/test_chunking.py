import pytest

from src.preprocessing.chunking import CHUNKING_CONFIG, TextChunk, TextChunker


class TestChunkingConfig:
    """Tests for chunking configuration."""

    def test_config_has_required_keys(self):
        """Verify CHUNKING_CONFIG has all required keys."""
        assert "chunk_size" in CHUNKING_CONFIG
        assert "chunk_overlap" in CHUNKING_CONFIG
        assert "separator" in CHUNKING_CONFIG

    def test_config_default_values(self):
        """Verify default configuration values."""
        assert CHUNKING_CONFIG["chunk_size"] == 1000
        assert CHUNKING_CONFIG["chunk_overlap"] == 200
        assert CHUNKING_CONFIG["separator"] == "\n\n"


class TestTextChunk:
    """Tests for TextChunk dataclass."""

    def test_textchunk_creation(self):
        """Test TextChunk can be created with required fields."""
        chunk = TextChunk(
            content="test content",
            chunk_index=0,
            start_char=0,
            end_char=12,
        )

        assert chunk.content == "test content"
        assert chunk.chunk_index == 0
        assert chunk.start_char == 0
        assert chunk.end_char == 12
        assert chunk.metadata is None

    def test_textchunk_with_metadata(self):
        """Test TextChunk with optional metadata."""
        chunk = TextChunk(
            content="test",
            chunk_index=1,
            start_char=10,
            end_char=14,
            metadata={"page": 1, "source": "test.pdf"},
        )

        assert chunk.metadata == {"page": 1, "source": "test.pdf"}


class TestTextChunker:
    """Tests for TextChunker class."""

    @pytest.fixture
    def chunker(self):
        """Create a TextChunker with default config."""
        return TextChunker()

    @pytest.fixture
    def small_chunker(self):
        """Create a TextChunker with small chunk size for testing."""
        return TextChunker(chunk_size=50, chunk_overlap=10)

    def test_chunker_default_config(self, chunker):
        """Test chunker uses default config values."""
        assert chunker.chunk_size == 1000
        assert chunker.chunk_overlap == 200
        assert chunker.separator == "\n\n"

    def test_chunker_custom_config(self):
        """Test chunker accepts custom configuration."""
        chunker = TextChunker(
            chunk_size=500,
            chunk_overlap=100,
            separator="\n",
        )

        assert chunker.chunk_size == 500
        assert chunker.chunk_overlap == 100
        assert chunker.separator == "\n"

    def test_chunker_overlap_validation(self):
        """Test chunker rejects overlap >= chunk_size."""
        with pytest.raises(ValueError, match="chunk_overlap must be less than chunk_size"):
            TextChunker(chunk_size=100, chunk_overlap=100)

        with pytest.raises(ValueError, match="chunk_overlap must be less than chunk_size"):
            TextChunker(chunk_size=100, chunk_overlap=150)

    def test_chunk_empty_text(self, chunker):
        """Test empty text returns empty list."""
        assert chunker.chunk("") == []
        assert chunker.chunk("   ") == []
        assert chunker.chunk("\n\n") == []

    def test_chunk_small_text(self, chunker):
        """Test text smaller than chunk_size returns single chunk."""
        text = "This is a small text."
        chunks = chunker.chunk(text)

        assert len(chunks) == 1
        assert chunks[0].content == text
        assert chunks[0].chunk_index == 0
        assert chunks[0].start_char == 0
        assert chunks[0].end_char == len(text)

    def test_chunk_with_paragraphs(self, small_chunker):
        """Test text with paragraphs is split correctly."""
        text = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
        chunks = small_chunker.chunk(text)

        assert len(chunks) >= 2
        assert chunks[0].chunk_index == 0
        assert chunks[1].chunk_index == 1

    def test_chunk_indices_sequential(self, small_chunker):
        """Test chunk indices are sequential starting from 0."""
        text = "A" * 100 + "\n\n" + "B" * 100 + "\n\n" + "C" * 100
        chunks = small_chunker.chunk(text)

        for i, chunk in enumerate(chunks):
            assert chunk.chunk_index == i

    def test_chunk_overlap_content(self):
        """Test consecutive chunks have overlapping content."""
        chunker = TextChunker(chunk_size=30, chunk_overlap=10)
        text = "word1 word2 word3\n\nword4 word5 word6\n\nword7 word8 word9"
        chunks = chunker.chunk(text)

        if len(chunks) >= 2:
            # The end of chunk[0] should appear at the start of chunk[1]
            # due to overlap
            chunk0_end = chunks[0].content[-10:]
            chunk1_start = chunks[1].content[:15]
            # There should be some shared content
            assert any(
                word in chunk1_start
                for word in chunk0_end.split()
                if word.strip()
            ) or len(chunks) == 1

    def test_chunk_long_paragraph(self, small_chunker):
        """Test paragraph longer than chunk_size is split at word boundary."""
        # Create a long paragraph without separators
        text = " ".join(["word"] * 20)  # ~100 characters
        chunks = small_chunker.chunk(text)

        assert len(chunks) >= 2
        # All chunks should end cleanly (not mid-word)
        for chunk in chunks:
            assert not chunk.content.endswith("wor")

    def test_chunk_unicode_text(self, chunker):
        """Test Unicode characters are handled correctly."""
        text = "こんにちは世界\n\nПривет мир\n\n你好世界"
        chunks = chunker.chunk(text)

        assert len(chunks) >= 1
        # All original text should be present across chunks
        all_content = "".join(c.content for c in chunks)
        assert "こんにちは世界" in all_content or "こんにちは世界" in chunks[0].content

    def test_chunk_preserves_all_content(self, small_chunker):
        """Test that chunking preserves all original content."""
        text = "Paragraph one content.\n\nParagraph two content.\n\nParagraph three content."
        chunks = small_chunker.chunk(text)

        # Key words from each paragraph should appear in chunks
        all_content = " ".join(c.content for c in chunks)
        assert "one" in all_content
        assert "two" in all_content
        assert "three" in all_content

    def test_chunk_single_paragraph_large(self):
        """Test single large paragraph without separators."""
        chunker = TextChunker(chunk_size=50, chunk_overlap=10)
        text = "This is a very long paragraph that does not contain any separator characters and should be split into multiple chunks based on word boundaries."
        chunks = chunker.chunk(text)

        assert len(chunks) >= 2
        # First chunk should be under chunk_size
        assert len(chunks[0].content) <= 50

    def test_chunk_positions_valid(self, small_chunker):
        """Test start_char and end_char are valid positions."""
        text = "First part.\n\nSecond part.\n\nThird part."
        chunks = small_chunker.chunk(text)

        for chunk in chunks:
            assert chunk.start_char >= 0
            assert chunk.end_char > chunk.start_char
            assert chunk.end_char - chunk.start_char == len(chunk.content)

    def test_sentence_splitting(self):
        """Test that long paragraphs are split by sentences first."""
        chunker = TextChunker(chunk_size=80, chunk_overlap=15)
        # Long paragraph with multiple sentences
        text = "First sentence here. Second sentence here. Third sentence here. Fourth sentence here."
        chunks = chunker.chunk(text)

        # Should split into multiple chunks
        assert len(chunks) >= 2
        # Sentences should not be cut mid-way (no partial sentences ending with incomplete words)
        for chunk in chunks:
            # Check chunk doesn't end mid-sentence (unless it's the last chunk)
            content = chunk.content.strip()
            if chunk.chunk_index < len(chunks) - 1:
                # Non-final chunks should ideally end with sentence boundaries
                # or at least not cut words
                assert not content.endswith("her")

    def test_split_into_sentences_method(self):
        """Test _split_into_sentences helper method."""
        chunker = TextChunker()

        # Test basic sentence splitting
        text = "First sentence. Second sentence! Third sentence?"
        sentences = chunker._split_into_sentences(text)
        assert len(sentences) == 3
        assert sentences[0] == "First sentence."
        assert sentences[1] == "Second sentence!"
        assert sentences[2] == "Third sentence?"

        # Test single sentence
        single = chunker._split_into_sentences("Just one sentence.")
        assert len(single) == 1

        # Test empty string
        empty = chunker._split_into_sentences("")
        assert len(empty) == 0

    def test_chunk_to_db_records(self):
        """Test chunk_to_db_records returns database-ready dicts."""
        chunker = TextChunker(chunk_size=50, chunk_overlap=10)
        text = "First paragraph.\n\nSecond paragraph."

        records = chunker.chunk_to_db_records(text, document_id=123)

        assert len(records) >= 1
        # Check first record structure
        first = records[0]
        assert first["document_id"] == 123
        assert first["chunk_index"] == 0
        assert "content" in first
        assert "metadata" in first
        assert "start_char" in first["metadata"]
        assert "end_char" in first["metadata"]

    def test_chunk_to_db_records_with_extra_metadata(self):
        """Test chunk_to_db_records includes extra metadata."""
        chunker = TextChunker()
        text = "Sample text for testing."

        extra = {"source": "test.pdf", "page": 1}
        records = chunker.chunk_to_db_records(text, document_id=42, extra_metadata=extra)

        assert len(records) == 1
        metadata = records[0]["metadata"]
        assert metadata["source"] == "test.pdf"
        assert metadata["page"] == 1
        assert "start_char" in metadata
        assert "end_char" in metadata


class TestTextChunkToDbRecord:
    """Tests for TextChunk.to_db_record() method."""

    def test_to_db_record_basic(self):
        """Test to_db_record returns correct structure."""
        chunk = TextChunk(
            content="test content",
            chunk_index=0,
            start_char=0,
            end_char=12,
        )

        record = chunk.to_db_record(document_id=100)

        assert record["document_id"] == 100
        assert record["chunk_index"] == 0
        assert record["content"] == "test content"
        assert record["metadata"]["start_char"] == 0
        assert record["metadata"]["end_char"] == 12

    def test_to_db_record_with_extra_metadata(self):
        """Test to_db_record merges extra metadata."""
        chunk = TextChunk(
            content="test",
            chunk_index=1,
            start_char=10,
            end_char=14,
            metadata={"existing": "value"},
        )

        record = chunk.to_db_record(document_id=50, extra_metadata={"new": "data"})

        metadata = record["metadata"]
        assert metadata["existing"] == "value"
        assert metadata["new"] == "data"
        assert metadata["start_char"] == 10
        assert metadata["end_char"] == 14

    def test_to_db_record_with_none_metadata(self):
        """Test to_db_record handles None metadata correctly."""
        chunk = TextChunk(
            content="test",
            chunk_index=0,
            start_char=0,
            end_char=4,
            metadata=None,
        )

        record = chunk.to_db_record(document_id=1)

        assert "metadata" in record
        assert record["metadata"]["start_char"] == 0
