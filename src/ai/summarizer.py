"""
Structured summary generation for YouTube videos.
"""
import logging
from dataclasses import dataclass

from src.ai.client import generate
from src.ai.prompts import (
    build_summary_prompt,
    build_deepdive_prompt,
    build_actionpoints_prompt,
    DEFAULT_LANGUAGE,
)
from src.transcript.chunker import chunk_transcript

logger = logging.getLogger(__name__)

# Max transcript chars to send to LLM (Gemini 1.5 Flash handles ~750k words,
# but we cap at 200k chars to keep responses snappy)
_MAX_TRANSCRIPT_CHARS = 200_000


def _truncate_transcript(transcript: str) -> str:
    """Truncate or chunk transcript for LLM context limits."""
    if len(transcript) <= _MAX_TRANSCRIPT_CHARS:
        return transcript
    # For very long transcripts, take first + last portions for better coverage
    half = _MAX_TRANSCRIPT_CHARS // 2
    first_half = transcript[:half]
    last_half = transcript[-half:]
    logger.info("Transcript truncated: %d chars → %d chars", len(transcript), _MAX_TRANSCRIPT_CHARS)
    return (
        first_half
        + "\n\n[... transcript continues ...]\n\n"
        + last_half
    )


def generate_summary(transcript: str, language: str = DEFAULT_LANGUAGE) -> str:
    """
    Generate a structured summary of a video transcript.

    Returns a formatted string with key points, timestamps, and core takeaway.

    Args:
        transcript: Full or timestamped transcript text.
        language:   Target response language (e.g. "English", "Hindi (हिंदी)").

    Returns:
        Formatted summary string ready to send to Telegram.
    """
    trimmed = _truncate_transcript(transcript)
    prompt = build_summary_prompt(trimmed, language)
    logger.info("Generating summary in %s (%d chars of transcript)", language, len(trimmed))
    return generate(prompt)


def generate_deepdive(transcript: str, language: str = DEFAULT_LANGUAGE) -> str:
    """
    Generate an in-depth analysis of a video transcript.

    Args:
        transcript: Full transcript text.
        language:   Target response language.

    Returns:
        Formatted deep-dive analysis string.
    """
    trimmed = _truncate_transcript(transcript)
    prompt = build_deepdive_prompt(trimmed, language)
    logger.info("Generating deep-dive in %s", language)
    return generate(prompt)


def generate_action_points(transcript: str, language: str = DEFAULT_LANGUAGE) -> str:
    """
    Extract actionable items from a video transcript.

    Args:
        transcript: Full transcript text.
        language:   Target response language.

    Returns:
        Formatted action points string.
    """
    trimmed = _truncate_transcript(transcript)
    prompt = build_actionpoints_prompt(trimmed, language)
    logger.info("Generating action points in %s", language)
    return generate(prompt)
