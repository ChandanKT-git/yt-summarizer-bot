"""
YouTube URL validation and video ID extraction.
Handles all known YouTube URL patterns.
"""
import re
from urllib.parse import urlparse, parse_qs

# All known YouTube URL patterns
_YT_PATTERNS = [
    # Standard watch URL: https://www.youtube.com/watch?v=VIDEO_ID
    r"(?:https?://)?(?:www\.)?youtube\.com/watch\?.*v=([a-zA-Z0-9_-]{11})",
    # Short URL: https://youtu.be/VIDEO_ID
    r"(?:https?://)?youtu\.be/([a-zA-Z0-9_-]{11})",
    # Shorts: https://www.youtube.com/shorts/VIDEO_ID
    r"(?:https?://)?(?:www\.)?youtube\.com/shorts/([a-zA-Z0-9_-]{11})",
    # Embedded: https://www.youtube.com/embed/VIDEO_ID
    r"(?:https?://)?(?:www\.)?youtube\.com/embed/([a-zA-Z0-9_-]{11})",
    # Mobile: https://m.youtube.com/watch?v=VIDEO_ID
    r"(?:https?://)?m\.youtube\.com/watch\?.*v=([a-zA-Z0-9_-]{11})",
]

_COMPILED_PATTERNS = [re.compile(p) for p in _YT_PATTERNS]


def extract_video_id(url: str) -> str | None:
    """
    Extract YouTube video ID from any known URL format.

    Returns the 11-character video ID, or None if not a valid YouTube URL.

    Examples:
        extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ") -> "dQw4w9WgXcQ"
        extract_video_id("https://youtu.be/dQw4w9WgXcQ")                -> "dQw4w9WgXcQ"
        extract_video_id("https://youtube.com/shorts/dQw4w9WgXcQ")      -> "dQw4w9WgXcQ"
        extract_video_id("https://example.com")                         -> None
    """
    if not url or not isinstance(url, str):
        return None

    url = url.strip()

    for pattern in _COMPILED_PATTERNS:
        match = pattern.search(url)
        if match:
            video_id = match.group(1)
            # Validate the extracted ID is exactly 11 characters with valid chars
            if re.match(r"^[a-zA-Z0-9_-]{11}$", video_id):
                return video_id

    return None


def is_valid_youtube_url(url: str) -> bool:
    """Return True if the string is a recognizable YouTube video URL."""
    return extract_video_id(url) is not None


def build_watch_url(video_id: str) -> str:
    """Build a canonical watch URL from a video ID."""
    return f"https://www.youtube.com/watch?v={video_id}"
