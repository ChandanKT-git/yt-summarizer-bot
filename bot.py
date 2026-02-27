"""
YT Summarizer Bot — Main Entry Point

Initialises the Telegram application, registers all handlers,
and starts polling. Also launches the OpenClaw skill HTTP endpoint.

Local Telegram Bot API Server Support
--------------------------------------
If LOCAL_BOT_API_SERVER_URL is set in .env (e.g. "http://localhost:8081"),
the bot connects to that local server instead of api.telegram.org.
This is useful when Telegram's public servers are blocked on your network.

To start the local server:
    docker compose up -d telegram-bot-api
"""
import asyncio
import logging
import sys
from threading import Thread

from telegram import BotCommand
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
)

from config import Config
from src.handlers.commands import (
    cmd_start,
    cmd_help,
    cmd_summary,
    cmd_deepdive,
    cmd_actionpoints,
    cmd_language,
    cmd_clear,
)
from src.handlers.messages import handle_message

# ── Logging ────────────────────────────────────────────────────────────────────

logging.basicConfig(
    format="%(asctime)s | %(levelname)-8s | %(name)s — %(message)s",
    level=getattr(logging, Config.LOG_LEVEL.upper(), logging.INFO),
    handlers=[logging.StreamHandler(sys.stdout)],
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# ── Bot commands shown in Telegram UI ─────────────────────────────────────────

BOT_COMMANDS = [
    BotCommand("start",        "Welcome & quick start guide"),
    BotCommand("help",         "Full command reference"),
    BotCommand("summary",      "Re-send summary of current video"),
    BotCommand("deepdive",     "In-depth analysis of current video"),
    BotCommand("actionpoints", "Extract action items from current video"),
    BotCommand("language",     "Switch output language (e.g. /language Hindi)"),
    BotCommand("clear",        "Clear session and start fresh"),
]


# ── Optional: OpenClaw skill HTTP endpoint ─────────────────────────────────────

def start_openclaw_skill_server() -> None:
    """
    Start a lightweight HTTP server as an OpenClaw skill endpoint.
    Runs in a background daemon thread.
    """
    try:
        from aiohttp import web

        async def skill_handler(request: web.Request) -> web.Response:
            data = await request.json()
            logger.info("OpenClaw skill request: %s", data)
            return web.json_response({
                "status": "ok",
                "message": "YT Summarizer skill is active. Send a YouTube URL via Telegram.",
            })

        async def health_handler(request: web.Request) -> web.Response:
            from src.session.manager import session_manager
            return web.json_response({
                "status": "healthy",
                "active_sessions": session_manager.session_count(),
                "cached_transcripts": session_manager.cache_size(),
            })

        async def run_server() -> None:
            app = web.Application()
            app.router.add_post("/openclaw/skill", skill_handler)
            app.router.add_get("/health", health_handler)
            runner = web.AppRunner(app)
            await runner.setup()
            site = web.TCPSite(runner, "0.0.0.0", Config.OPENCLAW_SKILL_PORT)
            await site.start()
            logger.info("OpenClaw skill endpoint running on port %d", Config.OPENCLAW_SKILL_PORT)
            while True:
                await asyncio.sleep(3600)

        thread = Thread(target=lambda: asyncio.run(run_server()), daemon=True, name="openclaw-skill")
        thread.start()
        logger.info("OpenClaw skill server thread started")

    except Exception as e:
        logger.warning("Could not start OpenClaw skill server: %s", e)


# ── Build Telegram Application ─────────────────────────────────────────────────

def build_application() -> Application:
    """
    Build the Telegram Application object.

    If LOCAL_BOT_API_SERVER_URL is configured, the bot will talk to that
    local server (e.g. http://localhost:8081) instead of api.telegram.org.
    This lets you run the bot on networks where Telegram is blocked.
    """
    builder: ApplicationBuilder = Application.builder().token(Config.TELEGRAM_BOT_TOKEN)

    local_url = Config.LOCAL_BOT_API_SERVER_URL
    if local_url:
        # Strip trailing slash for clean concatenation
        base = local_url.rstrip("/")
        builder = (
            builder
            .base_url(f"{base}/bot")
            .base_file_url(f"{base}/file/bot")
            .local_mode(True)   # Enables local-server-specific features (e.g. larger uploads)
        )
        logger.info("🔌 Using LOCAL Telegram Bot API server: %s", base)
    else:
        logger.info("🌐 Using Telegram's public API server (api.telegram.org)")

    builder = builder.post_init(post_init)
    return builder.build()


# ── Lifecycle ──────────────────────────────────────────────────────────────────

async def post_init(application: Application) -> None:
    """Called after application initialises — register bot commands in Telegram."""
    await application.bot.set_my_commands(BOT_COMMANDS)
    logger.info("Bot commands registered")


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    logger.info("Starting YT Summarizer Bot…")

    # Start OpenClaw skill server in background
    start_openclaw_skill_server()

    # Build the application (with optional local API server support)
    app = build_application()

    # ── Register command handlers ─────────────────────────────────────────
    app.add_handler(CommandHandler("start",        cmd_start))
    app.add_handler(CommandHandler("help",         cmd_help))
    app.add_handler(CommandHandler("summary",      cmd_summary))
    app.add_handler(CommandHandler("deepdive",     cmd_deepdive))
    app.add_handler(CommandHandler("actionpoints", cmd_actionpoints))
    app.add_handler(CommandHandler("language",     cmd_language))
    app.add_handler(CommandHandler("clear",        cmd_clear))

    # ── Register message handler (non-command text) ───────────────────────
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # ── Start polling ─────────────────────────────────────────────────────
    logger.info("Bot is running. Press Ctrl+C to stop.")
    app.run_polling(
        drop_pending_updates=True,
        allowed_updates=["message"],
    )


if __name__ == "__main__":
    main()
