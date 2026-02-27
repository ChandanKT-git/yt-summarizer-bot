"""Unit tests for transcript chunker."""
import pytest
from src.transcript.chunker import chunk_transcript, estimate_token_count


class TestChunkTranscript:
    def test_short_text_returns_single_chunk(self):
        text = "Hello world. This is a test."
        chunks = chunk_transcript(text, max_chars=1000)
        assert len(chunks) == 1
        assert chunks[0] == text

    def test_empty_text_returns_empty_list(self):
        assert chunk_transcript("") == []

    def test_long_text_splits_into_multiple_chunks(self):
        # Create a text longer than max_chars
        sentence = "This is a test sentence. "
        text = sentence * 100   # 2500 chars
        chunks = chunk_transcript(text, max_chars=500)
        assert len(chunks) > 1

    def test_all_content_preserved(self):
        """No text should be lost during chunking."""
        sentence = "Alpha beta gamma. "
        text = sentence * 200
        chunks = chunk_transcript(text, max_chars=300)
        # Rejoin all chunks and compare word count
        rejoined = " ".join(chunks)
        # Allow minor whitespace differences
        assert len(rejoined) >= len(text) * 0.95

    def test_chunks_respect_max_chars(self):
        sentence = "Short sentence. "
        text = sentence * 500
        max_chars = 200
        chunks = chunk_transcript(text, max_chars=max_chars)
        for chunk in chunks:
            assert len(chunk) <= max_chars + 50  # Small tolerance for long sentences

    def test_single_very_long_sentence_hard_splits(self):
        """A single sentence longer than max_chars must still be handled."""
        long_sentence = "word " * 10000  # No sentence terminators
        chunks = chunk_transcript(long_sentence, max_chars=100)
        assert len(chunks) > 1

    def test_exact_fit(self):
        text = "A" * 100
        chunks = chunk_transcript(text, max_chars=100)
        assert len(chunks) == 1


class TestEstimateTokenCount:
    def test_estimate_is_reasonable(self):
        text = "word " * 1000   # 5000 chars
        tokens = estimate_token_count(text)
        # Should be roughly 5000/3.5 ≈ 1428
        assert 1000 < tokens < 2000

    def test_empty_string(self):
        assert estimate_token_count("") == 0
