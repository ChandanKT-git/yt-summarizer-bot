"""
Q&A module — answers user questions grounded in the video transcript.
"""
import logging

from src.ai.client import generate
from src.ai.prompts import build_qa_prompt, DEFAULT_LANGUAGE

logger = logging.getLogger(__name__)

# Max transcript chars to send for Q&A context
_MAX_TRANSCRIPT_CHARS = 200_000


def answer_question(
    question: str,
    transcript: str,
    history: list[tuple[str, str]] | None = None,
    language: str = DEFAULT_LANGUAGE,
) -> str:
    """
    Answer a user question based solely on the video transcript.

    If the answer is not in the transcript, returns the standard
    "not covered" message so users know it's outside video scope.

    Args:
        question:   The user's question.
        transcript: Full video transcript text.
        history:    Previous (question, answer) pairs for context (last N turns).
        language:   Target response language.

    Returns:
        Answer string, or "❌ This topic is not covered in the video." if not found.
    """
    if not transcript or not transcript.strip():
        logger.warning("Q&A called with empty transcript")
        return "⚠️ No transcript is loaded. Please send a YouTube link first."

    # Trim transcript to fit context window
    trimmed = transcript[:_MAX_TRANSCRIPT_CHARS] if len(transcript) > _MAX_TRANSCRIPT_CHARS else transcript

    prompt = build_qa_prompt(
        transcript=trimmed,
        question=question,
        history=history or [],
        language=language,
    )

    logger.info("Answering question in %s: %s", language, question[:80])
    return generate(prompt)
