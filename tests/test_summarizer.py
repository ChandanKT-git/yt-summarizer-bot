"""Integration tests for AI summarizer (with mocked Gemini client)."""
import pytest
from unittest.mock import patch, MagicMock

from src.ai.summarizer import generate_summary, generate_deepdive, generate_action_points
from src.ai.qa import answer_question
from src.ai.prompts import normalize_language, build_summary_prompt, build_qa_prompt


SAMPLE_TRANSCRIPT = """
[00:00] Welcome to this video about Python best practices.
[00:30] Today we will cover type hints, testing, and code structure.
[02:00] Type hints help your IDE and colleagues understand your code.
[05:00] Always write tests using pytest for reliable code.
[08:00] Keep your functions small and focused on a single task.
[10:00] Thank you for watching!
"""


class TestNormalizeLanguage:
    def test_english(self):
        assert normalize_language("English") == "English"

    def test_hindi_lowercase(self):
        assert normalize_language("hindi") == "Hindi (हिंदी)"

    def test_tamil(self):
        assert normalize_language("tamil") == "Tamil (தமிழ்)"

    def test_unknown_defaults_to_english(self):
        assert normalize_language("klingon") == "English"

    def test_case_insensitive(self):
        assert normalize_language("HINDI") == "Hindi (हिंदी)"


class TestBuildPrompts:
    def test_summary_prompt_contains_transcript(self):
        prompt = build_summary_prompt(SAMPLE_TRANSCRIPT, "English")
        assert "Python best practices" in prompt
        assert "English" in prompt

    def test_qa_prompt_contains_question_and_history(self):
        history = [("What is this about?", "This is about Python.")]
        prompt = build_qa_prompt(SAMPLE_TRANSCRIPT, "Tell me about testing", history, "English")
        assert "Tell me about testing" in prompt
        assert "What is this about?" in prompt
        assert "This is about Python." in prompt

    def test_qa_prompt_empty_history(self):
        prompt = build_qa_prompt(SAMPLE_TRANSCRIPT, "What is discussed?", [], "English")
        assert "No previous conversation" in prompt


class TestGenerateSummary:
    @patch("src.ai.summarizer.generate")
    def test_generate_summary_calls_generate(self, mock_generate):
        mock_generate.return_value = "🎥 Mock Summary\n📌 Key points..."
        result = generate_summary(SAMPLE_TRANSCRIPT, "English")
        assert mock_generate.called
        assert "Mock Summary" in result

    @patch("src.ai.summarizer.generate")
    def test_generate_summary_in_hindi(self, mock_generate):
        mock_generate.return_value = "🎥 हिंदी सारांश"
        result = generate_summary(SAMPLE_TRANSCRIPT, "Hindi (हिंदी)")
        # Prompt should request Hindi
        call_args = mock_generate.call_args[0][0]
        assert "Hindi" in call_args

    @patch("src.ai.summarizer.generate")
    def test_generate_deepdive(self, mock_generate):
        mock_generate.return_value = "📖 Detailed Analysis..."
        result = generate_deepdive(SAMPLE_TRANSCRIPT)
        assert mock_generate.called

    @patch("src.ai.summarizer.generate")
    def test_generate_action_points(self, mock_generate):
        mock_generate.return_value = "✅ Action 1\n✅ Action 2"
        result = generate_action_points(SAMPLE_TRANSCRIPT)
        assert mock_generate.called


class TestAnswerQuestion:
    @patch("src.ai.qa.generate")
    def test_answer_question_uses_transcript(self, mock_generate):
        mock_generate.return_value = "Around 5:00, the speaker mentions pytest for testing."
        result = answer_question("What is said about testing?", SAMPLE_TRANSCRIPT)
        assert mock_generate.called
        assert "pytest" in result

    @patch("src.ai.qa.generate")
    def test_empty_transcript_returns_warning(self, mock_generate):
        result = answer_question("What?", "")
        mock_generate.assert_not_called()
        assert "No transcript" in result

    @patch("src.ai.qa.generate")
    def test_answer_with_history(self, mock_generate):
        mock_generate.return_value = "Yes, as mentioned previously, pytest is used."
        history = [("What tools are mentioned?", "pytest is mentioned.")]
        result = answer_question("Is pytest used?", SAMPLE_TRANSCRIPT, history)
        call_args = mock_generate.call_args[0][0]
        assert "pytest is mentioned" in call_args  # History is included in prompt
