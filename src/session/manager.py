"""
Per-user session management with transcript caching.

Sessions hold each user's current video context, language preference,
and Q&A history. The transcript cache is shared across all users
(same video doesn't get re-fetched).
"""
import logging
from dataclasses import dataclass, field
from typing import Optional

from cachetools import TTLCache

from config import Config
from src.transcript.fetcher import TranscriptResult

logger = logging.getLogger(__name__)


@dataclass
class UserSession:
    """Holds per-user state for the current video conversation."""
    user_id: int
    video_id: Optional[str] = None
    transcript: Optional[str] = None          # Full timestamped transcript text
    summary: Optional[str] = None             # Cached summary for this video+lang
    language: str = "English"                 # User's preferred output language
    qa_history: list[tuple[str, str]] = field(default_factory=list)  # (question, answer)

    def has_video(self) -> bool:
        return bool(self.video_id and self.transcript)

    def add_qa(self, question: str, answer: str, max_history: int = 10) -> None:
        """Append a Q&A pair; trim history to last max_history entries."""
        self.qa_history.append((question, answer))
        if len(self.qa_history) > max_history:
            self.qa_history = self.qa_history[-max_history:]

    def clear_video(self) -> None:
        """Reset video-related state but keep language preference."""
        self.video_id = None
        self.transcript = None
        self.summary = None
        self.qa_history.clear()


class SessionManager:
    """
    Thread-safe in-memory session + transcript cache manager.

    - _sessions: user_id → UserSession (lives as long as bot runs)
    - _transcript_cache: video_id → TranscriptResult (TTL-based, shared)
    """

    def __init__(self) -> None:
        self._sessions: dict[int, UserSession] = {}
        self._transcript_cache: TTLCache = TTLCache(
            maxsize=Config.MAX_CACHE_SIZE,
            ttl=Config.CACHE_TTL_SECONDS,
        )

    # ── Session API ──────────────────────────────────────────────────────────

    def get_session(self, user_id: int) -> UserSession:
        """Return existing session or create a new one."""
        if user_id not in self._sessions:
            self._sessions[user_id] = UserSession(user_id=user_id)
            logger.debug("Created new session for user %d", user_id)
        return self._sessions[user_id]

    def clear_session(self, user_id: int) -> None:
        """Remove a user's session entirely."""
        self._sessions.pop(user_id, None)
        logger.debug("Cleared session for user %d", user_id)

    def set_language(self, user_id: int, language: str) -> None:
        session = self.get_session(user_id)
        session.language = language
        # Clear cached summary so next /summary re-generates in the new language
        session.summary = None

    def load_video(self, user_id: int, result: TranscriptResult, transcript_text: str) -> None:
        """Update the session with a newly-fetched video."""
        session = self.get_session(user_id)
        session.clear_video()
        session.video_id = result.video_id
        session.transcript = transcript_text
        logger.info("Loaded video %s for user %d", result.video_id, user_id)

    # ── Transcript cache API ─────────────────────────────────────────────────

    def get_cached_transcript(self, video_id: str) -> Optional[TranscriptResult]:
        """Return a cached TranscriptResult or None if not cached / expired."""
        result = self._transcript_cache.get(video_id)
        if result:
            logger.debug("Transcript cache HIT for %s", video_id)
        return result

    def cache_transcript(self, result: TranscriptResult) -> None:
        """Store a TranscriptResult in the shared cache."""
        self._transcript_cache[result.video_id] = result
        logger.debug("Transcript cached for %s", result.video_id)

    def cache_size(self) -> int:
        return len(self._transcript_cache)

    def session_count(self) -> int:
        return len(self._sessions)


# Module-level singleton used throughout the application
session_manager = SessionManager()
