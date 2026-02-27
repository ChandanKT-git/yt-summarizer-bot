"""
AI client — supports Groq (primary) and Google Gemini (fallback).

Provider selection is automatic based on which API key is set in .env:
  - GROQ_API_KEY set   → uses Groq (llama-3.3-70b, free tier: 30 RPM / 14,400 RPD)
  - GEMINI_API_KEY set → uses Google Gemini (v1 API)
  - Both set           → Groq is tried first, Gemini is fallback

Usage:
    from src.ai.client import generate
    text = generate("Summarize this: ...")
"""
import logging
import time

from config import Config
from src.ai.prompts import SYSTEM_PROMPT

logger = logging.getLogger(__name__)


# ── Groq models (free tier, OpenAI-compatible) ────────────────────────────────
_GROQ_MODELS = [
    "llama-3.3-70b-versatile",   # best quality, 32K context
    "llama-3.1-8b-instant",      # fastest, higher RPM
    "mixtral-8x7b-32768",        # good quality, 32K context
]

# ── Gemini models (v1 API) ────────────────────────────────────────────────────
_GEMINI_MODELS = [
    "gemini-2.0-flash-lite",
    "gemini-2.0-flash",
    "gemini-2.5-flash",
]


# ── Groq client ───────────────────────────────────────────────────────────────

_groq_client = None


def _get_groq_client():
    global _groq_client
    if _groq_client is None:
        from groq import Groq
        _groq_client = Groq(api_key=Config.GROQ_API_KEY)
        logger.info("Groq client initialized (primary model: %s)", _GROQ_MODELS[0])
    return _groq_client


def _generate_groq(prompt: str, max_retries: int = 3, initial_wait: float = 2.0) -> str:
    """Generate text using Groq's API."""
    client = _get_groq_client()

    for model_name in _GROQ_MODELS:
        for attempt in range(1, max_retries + 1):
            try:
                response = client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user",   "content": prompt},
                    ],
                    temperature=0.4,
                    max_tokens=4096,
                    top_p=0.9,
                )
                text = response.choices[0].message.content
                if not text:
                    raise ValueError("Groq returned an empty response.")
                if model_name != _GROQ_MODELS[0]:
                    logger.info("Used Groq fallback model: %s", model_name)
                return text

            except Exception as e:
                err_str = str(e).lower()

                # Model not found → try next model
                if "404" in err_str or "not found" in err_str or "model_not_found" in err_str:
                    logger.warning("Groq model %s not available, trying next: %s", model_name, e)
                    break

                # Quota / rate limit → retry with backoff then try next model
                is_quota = any(kw in err_str for kw in ("429", "quota", "rate_limit", "rate limit", "resource exhausted"))
                is_transient = is_quota or any(kw in err_str for kw in ("503", "service unavailable", "timeout"))

                if is_transient and attempt < max_retries:
                    wait = initial_wait * (2 ** (attempt - 1))
                    logger.warning("Groq transient error (attempt %d/%d), retrying in %.1fs: %s", attempt, max_retries, wait, e)
                    time.sleep(wait)
                    continue

                if is_quota:
                    logger.warning("Groq quota exhausted for model %s, trying next model.", model_name)
                    break

                logger.error("Groq API error (model=%s): %s", model_name, e)
                raise RuntimeError(f"Failed to generate AI response via Groq: {e}") from e

    raise RuntimeError(f"All Groq models failed. Tried: {_GROQ_MODELS}. Check your GROQ_API_KEY.")


# ── Gemini client ─────────────────────────────────────────────────────────────

_gemini_client = None


def _get_gemini_client():
    global _gemini_client
    if _gemini_client is None:
        from google import genai
        from google.genai import types
        _gemini_client = genai.Client(
            api_key=Config.GEMINI_API_KEY,
            http_options=types.HttpOptions(api_version="v1"),
        )
        logger.info("Gemini client initialized (v1 API, primary model: %s)", _GEMINI_MODELS[0])
    return _gemini_client


def _generate_gemini(prompt: str, max_retries: int = 3, initial_wait: float = 2.0) -> str:
    """Generate text using Gemini's v1 API."""
    from google.genai import types

    client = _get_gemini_client()

    for model_name in _GEMINI_MODELS:
        for attempt in range(1, max_retries + 1):
            try:
                # v1 API: pass system prompt as the first conversation turn
                contents = [
                    types.Content(role="user",  parts=[types.Part(text=f"[System Instructions]\n{SYSTEM_PROMPT}")]),
                    types.Content(role="model", parts=[types.Part(text="Understood. I'll follow those instructions.")]),
                    types.Content(role="user",  parts=[types.Part(text=prompt)]),
                ]
                response = client.models.generate_content(
                    model=model_name,
                    contents=contents,
                    config=types.GenerateContentConfig(temperature=0.4, top_p=0.9, max_output_tokens=4096),
                )
                text = response.text
                if not text:
                    raise ValueError("Gemini returned an empty response.")
                if model_name != _GEMINI_MODELS[0]:
                    logger.info("Used Gemini fallback model: %s", model_name)
                return text

            except Exception as e:
                err_str = str(e).lower()
                if "404" in err_str or "not found" in err_str:
                    logger.warning("Gemini model %s not available, trying next: %s", model_name, e)
                    break

                is_quota = any(kw in err_str for kw in ("429", "quota", "resource exhausted"))
                is_transient = is_quota or any(kw in err_str for kw in ("503", "service unavailable", "timeout"))

                if is_transient and attempt < max_retries:
                    wait = initial_wait * (2 ** (attempt - 1))
                    logger.warning("Gemini transient error (attempt %d/%d), retrying in %.1fs: %s", attempt, max_retries, wait, e)
                    time.sleep(wait)
                    continue

                if is_quota:
                    logger.warning("Gemini quota exhausted for model %s, trying next model.", model_name)
                    break

                logger.error("Gemini API error (model=%s): %s", model_name, e)
                raise RuntimeError(f"Failed to generate AI response via Gemini: {e}") from e

    raise RuntimeError(f"All Gemini models failed. Tried: {_GEMINI_MODELS}. Check your GEMINI_API_KEY.")


# ── Public interface ──────────────────────────────────────────────────────────

def generate(
    prompt: str,
    max_retries: int = 3,
    initial_wait: float = 2.0,
) -> str:
    """
    Generate text using the best available AI provider.

    Tries Groq first (if GROQ_API_KEY is set), then falls back to Gemini
    (if GEMINI_API_KEY is set). Raises RuntimeError if all providers fail.
    """
    errors = []

    if Config.GROQ_API_KEY:
        try:
            return _generate_groq(prompt, max_retries=max_retries, initial_wait=initial_wait)
        except RuntimeError as e:
            logger.warning("Groq failed, trying Gemini fallback: %s", e)
            errors.append(f"Groq: {e}")

    if Config.GEMINI_API_KEY:
        try:
            return _generate_gemini(prompt, max_retries=max_retries, initial_wait=initial_wait)
        except RuntimeError as e:
            errors.append(f"Gemini: {e}")

    raise RuntimeError(
        "All AI providers failed.\n" + "\n".join(errors) +
        "\nSet GROQ_API_KEY (console.groq.com) or GEMINI_API_KEY in .env."
    )
