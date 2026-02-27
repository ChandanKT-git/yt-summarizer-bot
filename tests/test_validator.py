"""Unit tests for YouTube URL validator."""
import pytest
from src.transcript.validator import extract_video_id, is_valid_youtube_url, build_watch_url


class TestExtractVideoId:
    """Tests for extract_video_id()"""

    def test_standard_watch_url(self):
        assert extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_www_less_url(self):
        assert extract_video_id("https://youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_short_url(self):
        assert extract_video_id("https://youtu.be/dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_short_url_with_params(self):
        assert extract_video_id("https://youtu.be/dQw4w9WgXcQ?t=30") == "dQw4w9WgXcQ"

    def test_shorts_url(self):
        assert extract_video_id("https://www.youtube.com/shorts/dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_embed_url(self):
        assert extract_video_id("https://www.youtube.com/embed/dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_mobile_url(self):
        assert extract_video_id("https://m.youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_url_with_extra_params(self):
        assert extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=42&pp=ygU") == "dQw4w9WgXcQ"

    def test_no_protocol(self):
        assert extract_video_id("youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_invalid_url(self):
        assert extract_video_id("https://example.com") is None

    def test_invalid_youtube_no_video(self):
        assert extract_video_id("https://youtube.com/channel/UC123") is None

    def test_empty_string(self):
        assert extract_video_id("") is None

    def test_none_input(self):
        assert extract_video_id(None) is None

    def test_random_text(self):
        assert extract_video_id("hello world") is None

    def test_too_short_id(self):
        # IDs are always 11 chars
        assert extract_video_id("https://youtu.be/abc") is None

    def test_underscore_and_hyphen_in_id(self):
        assert extract_video_id("https://youtu.be/abc-DE_fg12") == "abc-DE_fg12"


class TestIsValidYouTubeUrl:
    def test_valid_url(self):
        assert is_valid_youtube_url("https://youtu.be/dQw4w9WgXcQ") is True

    def test_invalid_url(self):
        assert is_valid_youtube_url("https://google.com") is False

    def test_empty(self):
        assert is_valid_youtube_url("") is False


class TestBuildWatchUrl:
    def test_builds_correct_url(self):
        assert build_watch_url("dQw4w9WgXcQ") == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
