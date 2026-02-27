"""
Telegram command handlers.

Implements:
  /start        — Welcome & usage
  /help         — Full command reference
  /summary      — Re-send cached summary of current video
  /deepdive     — Detailed analysis of current video
  /actionpoints — Extract action items from current video
  /language     — Switch output language
  /clear        — Clear session / start fresh
"""
import logging

from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from src.ai.summarizer import generate_summary, generate_deepdive, generate_action_points
from src.ai.prompts import SUPPORTED_LANGUAGES, normalize_language
from src.session.manager import session_manager

logger = logging.getLogger(__name__)

# ── Welcome / Help text ───────────────────────────────────────────────────────

_WELCOME_TEXT = """
👋 *Welcome to YT Summarizer Bot!*

I'm your personal AI research assistant for YouTube videos.

*How to use:*
1️⃣ Send me a YouTube link
2️⃣ I'll generate a structured summary
3️⃣ Ask me any questions about the video

*Example:*
`https://youtube.com/watch?v=dQw4w9WgXcQ`

Type /help to see all commands.
"""

_HELP_TEXT = """
📖 *YT Summarizer Bot — Command Reference*

*Core Usage*
• Send a YouTube URL → Get a structured summary
• Ask any question → Get answers from the video

*Commands*
/summary      — Re-send summary of current video
/deepdive     — In-depth analysis of current video
/actionpoints — Extract action items from video
/language     — Show available languages
/language Hindi — Switch to Hindi responses
/clear        — Clear session & start fresh
/help         — Show this message

*Supported Languages*
English (default), Hindi, Tamil, Kannada, Telugu, Marathi, Bengali, Gujarati, Punjabi, Malayalam

*Tips*
• You can ask multiple follow-up questions
• To summarize a new video, just send a new link
"""


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _send_long_message(update: Update, text: str) -> None:
    """Send a long message, splitting at 4096 chars if needed (Telegram limit)."""
    max_len = 4096
    # Split by newlines to avoid cutting mid-word
    if len(text) <= max_len:
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
        return

    parts = []
    current = []
    current_len = 0
    for line in text.split("\n"):
        if current_len + len(line) + 1 > max_len:
            parts.append("\n".join(current))
            current = [line]
            current_len = len(line)
        else:
            current.append(line)
            current_len += len(line) + 1
    if current:
        parts.append("\n".join(current))

    for part in parts:
        await update.message.reply_text(part, parse_mode=ParseMode.MARKDOWN)


async def _require_video(update: Update) -> bool:
    """Check user has an active video; send hint if not. Returns True if OK."""
    user_id = update.effective_user.id
    session = session_manager.get_session(user_id)
    if not session.has_video():
        await update.message.reply_text(
            "⚠️ No video loaded yet.\n\nSend me a YouTube link first! 🎥",
            parse_mode=ParseMode.MARKDOWN,
        )
        return False
    return True


# ── Command handlers ──────────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start — welcome message."""
    await update.message.reply_text(_WELCOME_TEXT, parse_mode=ParseMode.MARKDOWN)


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help — command reference."""
    await update.message.reply_text(_HELP_TEXT, parse_mode=ParseMode.MARKDOWN)


async def cmd_summary(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /summary — re-send or regenerate the current video summary."""
    if not await _require_video(update):
        return

    user_id = update.effective_user.id
    session = session_manager.get_session(user_id)

    # Use cached summary if available
    if session.summary:
        await _send_long_message(update, session.summary)
        return

    await update.message.reply_text("⏳ Generating summary…")
    try:
        summary = generate_summary(session.transcript, session.language)
        session.summary = summary
        await _send_long_message(update, summary)
    except Exception as e:
        logger.error("Summary generation failed for user %d: %s", user_id, e)
        await update.message.reply_text(f"❌ Failed to generate summary: {e}")


async def cmd_deepdive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /deepdive — in-depth analysis."""
    if not await _require_video(update):
        return

    user_id = update.effective_user.id
    session = session_manager.get_session(user_id)

    await update.message.reply_text("🔍 Generating deep-dive analysis… (this takes a moment)")
    try:
        result = generate_deepdive(session.transcript, session.language)
        await _send_long_message(update, result)
    except Exception as e:
        logger.error("Deep-dive failed for user %d: %s", user_id, e)
        await update.message.reply_text(f"❌ Deep-dive failed: {e}")


async def cmd_actionpoints(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /actionpoints — extract actionable items."""
    if not await _require_video(update):
        return

    user_id = update.effective_user.id
    session = session_manager.get_session(user_id)

    await update.message.reply_text("🎯 Extracting action points…")
    try:
        result = generate_action_points(session.transcript, session.language)
        await _send_long_message(update, result)
    except Exception as e:
        logger.error("Action points failed for user %d: %s", user_id, e)
        await update.message.reply_text(f"❌ Failed to extract action points: {e}")


async def cmd_language(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /language [name].

    /language          → list supported languages
    /language Hindi    → switch to Hindi
    """
    user_id = update.effective_user.id
    args = context.args  # List of args after the command

    if not args:
        lang_list = "\n".join(f"• {v}" for v in SUPPORTED_LANGUAGES.values())
        await update.message.reply_text(
            f"🌐 *Supported Languages:*\n{lang_list}\n\n"
            f"Usage: `/language Hindi`",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    lang_input = " ".join(args)
    canonical = normalize_language(lang_input)

    session_manager.set_language(user_id, canonical)
    session = session_manager.get_session(user_id)

    await update.message.reply_text(
        f"✅ Language switched to *{canonical}*\n\n"
        f"Future summaries and answers will be in {canonical}.\n"
        f"{'Use /summary to regenerate the current video summary.' if session.has_video() else ''}",
        parse_mode=ParseMode.MARKDOWN,
    )
    logger.info("User %d switched language to %s", user_id, canonical)


async def cmd_clear(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /clear — wipe user session."""
    user_id = update.effective_user.id
    session = session_manager.get_session(user_id)
    session.clear_video()
    await update.message.reply_text(
        "🗑️ Session cleared! Send a new YouTube link to get started.",
    )
    logger.info("User %d cleared their session", user_id)
