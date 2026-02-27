"""
Message handler — routes text messages to either the YouTube summarizer
or the Q&A engine based on content.

Flow:
  1. If message contains a YouTube URL → fetch transcript + generate summary
  2. If user has active video session → answer as Q&A
  3. Otherwise → prompt user to send a YouTube link
"""
import logging

from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode, ChatAction

from src.transcript.validator import extract_video_id
from src.transcript.fetcher import fetch_transcript, get_timestamped_text
from src.ai.summarizer import generate_summary
from src.ai.qa import answer_question
from src.ai.prompts import SUPPORTED_LANGUAGES, normalize_language
from src.session.manager import session_manager
from src.handlers.commands import _send_long_message

logger = logging.getLogger(__name__)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Main message router. Called for any non-command text message.
    """
    text = (update.message.text or "").strip()
    user_id = update.effective_user.id

    if not text:
        return

    # ── Language switch via natural language e.g., "Summarize in Hindi" ────
    lower = text.lower()
    for lang_key, lang_display in SUPPORTED_LANGUAGES.items():
        if lang_key in lower and ("summarize in" in lower or "explain in" in lower or "answer in" in lower or "in " + lang_key in lower):
            session_manager.set_language(user_id, lang_display)
            session = session_manager.get_session(user_id)
            await update.message.reply_text(
                f"✅ Switched to *{lang_display}*!\n"
                f"{'Use /summary to regenerate the summary.' if session.has_video() else 'Now send me a YouTube link!'}",
                parse_mode=ParseMode.MARKDOWN,
            )
            return

    # ── YouTube URL detection ───────────────────────────────────────────────
    video_id = _find_video_id_in_text(text)
    if video_id:
        await _handle_youtube_url(update, context, video_id, user_id)
        return

    # ── Q&A: user has active video ─────────────────────────────────────────
    session = session_manager.get_session(user_id)
    if session.has_video():
        await _handle_qa(update, context, text, user_id, session)
        return

    # ── No video loaded: nudge user ─────────────────────────────────────────
    await update.message.reply_text(
        "🎬 Send me a YouTube link to get started!\n\n"
        "Example:\n`https://youtube.com/watch?v=dQw4w9WgXcQ`",
        parse_mode=ParseMode.MARKDOWN,
    )


def _find_video_id_in_text(text: str) -> str | None:
    """Scan text for the first YouTube video ID (handles URLs in any position)."""
    # Each word might be a URL
    for word in text.split():
        vid = extract_video_id(word)
        if vid:
            return vid
    return None


async def _handle_youtube_url(
    update: Update, context: ContextTypes.DEFAULT_TYPE, video_id: str, user_id: int
) -> None:
    """Process a YouTube URL: fetch transcript → cache → summarize → reply."""
    session = session_manager.get_session(user_id)

    await update.message.chat.send_action(ChatAction.TYPING)
    status_msg = await update.message.reply_text("⏳ Fetching transcript…")

    # ── Check transcript cache ─────────────────────────────────────────────
    cached = session_manager.get_cached_transcript(video_id)
    if cached and cached.success:
        transcript_result = cached
        logger.info("Using cached transcript for %s (user %d)", video_id, user_id)
        await status_msg.edit_text("✅ Transcript loaded from cache! Generating summary…")
    else:
        # Fetch fresh transcript
        transcript_result = fetch_transcript(video_id)

        if not transcript_result.success:
            emoji = "⚠️"
            await status_msg.edit_text(
                f"{emoji} {transcript_result.error}\n\n"
                f"Please try a different video, or check if the URL is correct."
            )
            return

        if transcript_result.is_empty:
            await status_msg.edit_text("⚠️ The transcript appears empty for this video.")
            return

        session_manager.cache_transcript(transcript_result)
        await status_msg.edit_text(f"✅ Transcript fetched! Generating summary…")

    # ── Prepare transcript text (with timestamps for AI context) ─────────
    transcript_text = get_timestamped_text(transcript_result)

    # ── Load into user session ────────────────────────────────────────────
    session_manager.load_video(user_id, transcript_result, transcript_text)

    await update.message.chat.send_action(ChatAction.TYPING)

    # ── Generate summary ──────────────────────────────────────────────────
    try:
        summary = generate_summary(transcript_text, session.language)
        session.summary = summary
    except Exception as e:
        logger.error("Summary generation failed for user %d / video %s: %s", user_id, video_id, e)
        await status_msg.edit_text(f"❌ Failed to generate summary: {e}")
        return

    await status_msg.delete()
    await _send_long_message(update, summary)

    # ── Invite follow-up questions ────────────────────────────────────────
    await update.message.reply_text(
        "💬 _Ask me anything about this video!_\n"
        "Or use /deepdive for more detail, /actionpoints for next steps.",
        parse_mode=ParseMode.MARKDOWN,
    )


async def _handle_qa(
    update: Update, context: ContextTypes.DEFAULT_TYPE, question: str, user_id: int, session
) -> None:
    """Answer a question using the active video's transcript."""
    await update.message.chat.send_action(ChatAction.TYPING)

    try:
        answer = answer_question(
            question=question,
            transcript=session.transcript,
            history=session.qa_history[-10:],  # Last 10 turns
            language=session.language,
        )
        session.add_qa(question, answer, max_history=10)
        await _send_long_message(update, answer)
    except Exception as e:
        logger.error("Q&A failed for user %d: %s", user_id, e)
        await update.message.reply_text(f"❌ Couldn't answer: {e}")
