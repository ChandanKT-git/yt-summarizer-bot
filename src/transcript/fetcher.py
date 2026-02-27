"""
YouTube transcript fetcher using youtube-transcript-api v1.x.

Handles:
- Missing transcripts / disabled captions
- Non-English videos (falls back to available language)
- Rate limiting (exponential backoff)
- Long videos (returns raw text for chunker)

NOTE: youtube-transcript-api v1.x uses an instance-based API.
      YouTubeTranscriptApi() must be instantiated; static methods are removed.
"""
import logging
import time
from dataclasses import dataclass, field

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    NoTranscriptFound,
    TranscriptsDisabled,
    VideoUnavailable,
    CouldNotRetrieveTranscript,
)

logger = logging.getLogger(__name__)

# Languages to try in priority order
_DEFAULT_LANGUAGES = ["en", "en-US", "en-GB", "en-IN"]


@dataclass
class TranscriptSegment:
    """A single timed segment of the transcript."""
    text: str
    start: float   # seconds
    duration: float


@dataclass
class TranscriptResult:
    """Result of a transcript fetch operation."""
    video_id: str
    text: str                              # Full joined transcript
    segments: list[TranscriptSegment] = field(default_factory=list)
    language: str = "en"
    success: bool = True
    error: str | None = None

    @property
    def is_empty(self) -> bool:
        return not self.text.strip()


def _format_timestamp(seconds: float) -> str:
    """Convert float seconds to HH:MM:SS or MM:SS string."""
    s = int(seconds)
    h, remainder = divmod(s, 3600)
    m, sec = divmod(remainder, 60)
    if h:
        return f"{h:02d}:{m:02d}:{sec:02d}"
    return f"{m:02d}:{sec:02d}"


def get_timestamped_text(result: TranscriptResult) -> str:
    """Build a transcript string with timestamps, for better AI context."""
    if not result.segments:
        return result.text
    lines = []
    for seg in result.segments:
        ts = _format_timestamp(seg.start)
        lines.append(f"[{ts}] {seg.text.strip()}")
    return "\n".join(lines)


def fetch_transcript(
    video_id: str,
    preferred_languages: list[str] | None = None,
    max_retries: int = 3,
) -> TranscriptResult:
    """
    Fetch the transcript for a given YouTube video ID.

    Uses youtube-transcript-api v1.x instance-based API:
      - api.fetch(video_id, languages=[...]) for preferred languages
      - api.list(video_id) + find_* methods for fallback

    Args:
        video_id: 11-character YouTube video ID.
        preferred_languages: Language codes to try first. Defaults to English variants.
        max_retries: Number of retry attempts on transient errors.

    Returns:
        TranscriptResult with success=True and text, or success=False with error message.
    """
    langs = preferred_languages or _DEFAULT_LANGUAGES

    for attempt in range(1, max_retries + 1):
        try:
            # v1.x: instantiate per call (not thread-safe to share)
            api = YouTubeTranscriptApi()

            fetched = None
            language_used = langs[0]

            # ── Try preferred languages ─────────────────────────────────────
            try:
                fetched = api.fetch(video_id, languages=langs)
                # Try to detect actual language from fetched object
                if hasattr(fetched, 'language_code'):
                    language_used = fetched.language_code
            except NoTranscriptFound:
                logger.info(
                    "Preferred languages not found for %s, scanning available transcripts",
                    video_id,
                )
                # ── Fall back: scan all available transcripts ───────────────
                transcript_list = api.list(video_id)

                transcript_obj = None

                # Priority 1: manually-created in preferred langs
                try:
                    transcript_obj = transcript_list.find_manually_created_transcript(langs)
                except (NoTranscriptFound, Exception):
                    pass

                # Priority 2: auto-generated in preferred langs
                if transcript_obj is None:
                    try:
                        transcript_obj = transcript_list.find_generated_transcript(langs)
                    except (NoTranscriptFound, Exception):
                        pass

                # Priority 3: any transcript at all
                if transcript_obj is None:
                    for t in transcript_list:
                        transcript_obj = t
                        break

                if transcript_obj is None:
                    return TranscriptResult(
                        video_id=video_id,
                        text="",
                        success=False,
                        error="No transcript available for this video.",
                    )

                fetched = transcript_obj.fetch()
                language_used = transcript_obj.language_code

            if fetched is None:
                return TranscriptResult(
                    video_id=video_id,
                    text="",
                    success=False,
                    error="Could not retrieve transcript (unknown error).",
                )

            # ── Parse segments ──────────────────────────────────────────────
            # v1.x FetchedTranscript is iterable; snippets have .text/.start/.duration
            segments = []
            for snippet in fetched:
                segments.append(
                    TranscriptSegment(
                        text=getattr(snippet, "text", str(snippet)),
                        start=float(getattr(snippet, "start", 0.0)),
                        duration=float(getattr(snippet, "duration", 0.0)),
                    )
                )

            full_text = " ".join(seg.text for seg in segments)

            logger.info(
                "Fetched transcript for %s (%d segments, lang=%s)",
                video_id, len(segments), language_used,
            )
            return TranscriptResult(
                video_id=video_id,
                text=full_text,
                segments=segments,
                language=language_used,
                success=True,
            )

        except TranscriptsDisabled:
            return TranscriptResult(
                video_id=video_id, text="", success=False,
                error="Transcripts are disabled for this video.",
            )
        except VideoUnavailable:
            return TranscriptResult(
                video_id=video_id, text="", success=False,
                error="This video is unavailable or private.",
            )
        except CouldNotRetrieveTranscript as e:
            return TranscriptResult(
                video_id=video_id, text="", success=False,
                error=f"Could not retrieve transcript: {e}",
            )
        except Exception as e:
            err_str = str(e).lower()
            is_transient = any(
                kw in err_str
                for kw in ("429", "rate", "timeout", "connection", "network")
            )
            if is_transient and attempt < max_retries:
                wait = 2 ** attempt
                logger.warning(
                    "Transient error (attempt %d/%d), retrying in %ds: %s",
                    attempt, max_retries, wait, e,
                )
                time.sleep(wait)
                continue
            logger.error("Failed to fetch transcript for %s: %s", video_id, e)
            return TranscriptResult(
                video_id=video_id, text="", success=False,
                error=f"Unexpected error fetching transcript: {e}",
            )

    return TranscriptResult(
        video_id=video_id, text="", success=False,
        error="Failed to fetch transcript after multiple retries.",
    )
