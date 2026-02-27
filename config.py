"""
Configuration management - loads settings from environment variables.
"""
import os
from dotenv import load_dotenv

load_dotenv()


def _get_required(key: str) -> str:
    val = os.getenv(key)
    if not val:
        raise ValueError(
            f"Missing required environment variable: {key}. "
            f"Copy .env.example to .env and fill in your credentials."
        )
    return val


class Config:
    # ── Credentials ───────────────────────────────────────────────────────────
    TELEGRAM_BOT_TOKEN: str    = _get_required("TELEGRAM_BOT_TOKEN")
    # At least one AI key required — Groq is tried first, Gemini is fallback
    GROQ_API_KEY:   str | None = os.getenv("GROQ_API_KEY")   or None
    GEMINI_API_KEY: str | None = os.getenv("GEMINI_API_KEY") or None

    # ── Local Telegram Bot API Server (optional) ──────────────────────────────
    # Leave empty to use Telegram's own servers (api.telegram.org).
    # Set to "http://localhost:8081" when running the local telegram-bot-api server.
    # Also fill in TELEGRAM_API_ID and TELEGRAM_API_HASH from my.telegram.org/apps
    LOCAL_BOT_API_SERVER_URL: str | None = os.getenv("LOCAL_BOT_API_SERVER_URL") or None
    TELEGRAM_API_ID:   str | None = os.getenv("TELEGRAM_API_ID")   or None
    TELEGRAM_API_HASH: str | None = os.getenv("TELEGRAM_API_HASH") or None

    # ── General ───────────────────────────────────────────────────────────────
    LOG_LEVEL: str           = os.getenv("LOG_LEVEL", "INFO")
    MAX_CACHE_SIZE: int      = int(os.getenv("MAX_CACHE_SIZE", "100"))
    CACHE_TTL_SECONDS: int   = int(os.getenv("CACHE_TTL_SECONDS", "3600"))
    MAX_QA_HISTORY: int      = int(os.getenv("MAX_QA_HISTORY", "10"))
    OPENCLAW_SKILL_PORT: int = int(os.getenv("OPENCLAW_SKILL_PORT", "8080"))
