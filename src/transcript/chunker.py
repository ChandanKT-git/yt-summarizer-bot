"""
Transcript chunking for very long videos.

Gemini 1.5 Flash supports ~1M tokens (≈750k words), which covers most videos.
This module handles edge cases like 3+ hour videos or dense transcripts.
"""
import re

# Approximate characters per token (safe estimate for multilingual text)
_CHARS_PER_TOKEN = 3.5
# Default max tokens per chunk (well within model limits with room for prompt)
_DEFAULT_MAX_CHARS = 80_000  # ~22k tokens


def chunk_transcript(text: str, max_chars: int = _DEFAULT_MAX_CHARS) -> list[str]:
    """
    Split a transcript into chunks of at most max_chars characters.

    Splits on sentence boundaries ('. ', '! ', '? ', '\n') to preserve context.
    Returns a list of strings; if text fits in one chunk, returns [text].

    Args:
        text: The full transcript text.
        max_chars: Maximum characters per chunk (default: 80,000).

    Returns:
        List of transcript chunks.
    """
    if not text:
        return []

    # If the whole transcript fits, no chunking needed
    if len(text) <= max_chars:
        return [text]

    # Split into sentences using common terminators
    sentence_endings = re.compile(r"(?<=[.!?])\s+")
    sentences = sentence_endings.split(text)

    chunks: list[str] = []
    current_chunk: list[str] = []
    current_len = 0

    for sentence in sentences:
        sentence_len = len(sentence)

        # If adding this sentence would exceed the limit, flush
        if current_len + sentence_len > max_chars and current_chunk:
            chunks.append(" ".join(current_chunk))
            current_chunk = []
            current_len = 0

        # If a single sentence is longer than max_chars, hard-split it
        if sentence_len > max_chars:
            parts = [sentence[i : i + max_chars] for i in range(0, sentence_len, max_chars)]
            for part in parts:
                chunks.append(part)
            continue

        current_chunk.append(sentence)
        current_len += sentence_len + 1  # +1 for the space

    # Flush remaining
    if current_chunk:
        chunks.append(" ".join(current_chunk))

    return chunks


def estimate_token_count(text: str) -> int:
    """Rough token count estimate (chars / 3.5)."""
    return int(len(text) / _CHARS_PER_TOKEN)
