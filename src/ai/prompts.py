"""
All LLM prompt templates.

Prompts are parameterized by language to support multilingual output.
The Gemini model generates responses natively in the target language —
no separate translation step required.
"""

# ── Supported languages ────────────────────────────────────────────────────────

SUPPORTED_LANGUAGES: dict[str, str] = {
    "english":  "English",
    "hindi":    "Hindi (हिंदी)",
    "tamil":    "Tamil (தமிழ்)",
    "kannada":  "Kannada (ಕನ್ನಡ)",
    "telugu":   "Telugu (తెలుగు)",
    "marathi":  "Marathi (मराठी)",
    "bengali":  "Bengali (বাংলা)",
    "gujarati": "Gujarati (ગુજરાતી)",
    "punjabi":  "Punjabi (ਪੰਜਾਬੀ)",
    "malayalam":"Malayalam (മലയാളം)",
}

DEFAULT_LANGUAGE = "English"


def normalize_language(user_input: str) -> str:
    """
    Map a user-supplied language string to a canonical display name.
    Falls back to English if unrecognized.
    """
    key = user_input.strip().lower()
    return SUPPORTED_LANGUAGES.get(key, DEFAULT_LANGUAGE)


# ── System prompt ──────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are YT Summarizer Bot — a smart AI research assistant for YouTube videos.
You analyze video transcripts and help users understand content quickly.
Be concise, accurate, and always base your answers on the provided transcript.
Never hallucinate information that is not in the transcript.
"""


# ── Summary prompt ─────────────────────────────────────────────────────────────

SUMMARY_PROMPT_TEMPLATE = """\
You are analyzing a YouTube video transcript. Generate a clear, structured summary in **{language}**.

TRANSCRIPT:
{transcript}

Your response MUST follow this exact format (translate all labels to {language} if not English):

🎥 **[Video Title or best inferred title]**

📌 **Key Points**
1. [First key point]
2. [Second key point]
3. [Third key point]
4. [Fourth key point]
5. [Fifth key point]

⏱ **Important Timestamps**
• [MM:SS or HH:MM:SS] — [What happens at this moment]
• [MM:SS or HH:MM:SS] — [What happens at this moment]
• [MM:SS or HH:MM:SS] — [What happens at this moment]

🧠 **Core Takeaway**
[One to three sentences summarizing the most important insight from the video]

Rules:
- Write the entire response in {language}
- Be concise but meaningful — avoid filler words
- If the transcript lacks clear timestamps, infer approximate ones from context
- Do not add information not present in the transcript
"""


# ── Deep-dive prompt ───────────────────────────────────────────────────────────

DEEPDIVE_PROMPT_TEMPLATE = """\
You are analyzing a YouTube video transcript. Provide a comprehensive, in-depth analysis in **{language}**.

TRANSCRIPT:
{transcript}

Your response should include:

🎥 **[Video Title or best inferred title]**

📖 **Detailed Summary**
[3-5 paragraph detailed overview of the full content]

📌 **Key Points** (expanded with context)
1. [Point — explain with detail]
2. [Point — explain with detail]
3. [Point — explain with detail]
4. [Point — explain with detail]
5. [Point — explain with detail]

⏱ **Important Timestamps**
• [MM:SS] — [Detailed description of what's discussed]
(list at least 5)

💡 **Key Insights & Analysis**
[2-3 deeper insights or implications from the content]

🧠 **Core Takeaway**
[2-4 sentences with the most important lesson]

Write the entire response in {language}.
"""


# ── Action points prompt ───────────────────────────────────────────────────────

ACTIONPOINTS_PROMPT_TEMPLATE = """\
You are analyzing a YouTube video transcript. Extract clear, actionable items in **{language}**.

TRANSCRIPT:
{transcript}

Your response should follow this format:

🎯 **Action Points from the Video**

✅ **Immediate Actions** (do today/this week)
1. [Specific action]
2. [Specific action]
3. [Specific action]

📅 **Short-term Actions** (next 1-4 weeks)
1. [Specific action]
2. [Specific action]

🔮 **Long-term Actions** (1-3 months+)
1. [Specific action]
2. [Specific action]

📚 **Resources Mentioned**
• [Resource / tool / book / link mentioned in the video]

Rules:
- Only include actions explicitly or implicitly suggested in the video
- Be specific and actionable
- Write in {language}
"""


# ── Q&A prompt ─────────────────────────────────────────────────────────────────

QA_PROMPT_TEMPLATE = """\
You are a helpful assistant answering questions about a YouTube video. Answer in **{language}**.

VIDEO TRANSCRIPT:
{transcript}

CONVERSATION HISTORY:
{history}

USER QUESTION: {question}

Instructions:
- Answer ONLY based on information in the transcript above
- If the answer is NOT in the transcript, respond with exactly:
  "❌ This topic is not covered in the video."
- Be concise and direct
- Cite approximate timestamps when relevant (e.g., "Around 5:30, the speaker mentions...")
- Write the answer in {language}
"""


def build_summary_prompt(transcript: str, language: str = DEFAULT_LANGUAGE) -> str:
    return SUMMARY_PROMPT_TEMPLATE.format(transcript=transcript, language=language)


def build_deepdive_prompt(transcript: str, language: str = DEFAULT_LANGUAGE) -> str:
    return DEEPDIVE_PROMPT_TEMPLATE.format(transcript=transcript, language=language)


def build_actionpoints_prompt(transcript: str, language: str = DEFAULT_LANGUAGE) -> str:
    return ACTIONPOINTS_PROMPT_TEMPLATE.format(transcript=transcript, language=language)


def build_qa_prompt(
    transcript: str,
    question: str,
    history: list[tuple[str, str]],
    language: str = DEFAULT_LANGUAGE,
) -> str:
    """
    Build the Q&A prompt.

    Args:
        transcript: Full video transcript text.
        question:   The user's current question.
        history:    List of (user_question, bot_answer) tuples.
        language:   Target response language.
    """
    history_text = ""
    if history:
        turns = []
        for q, a in history:
            turns.append(f"User: {q}\nAssistant: {a}")
        history_text = "\n\n".join(turns)
    else:
        history_text = "(No previous conversation)"

    return QA_PROMPT_TEMPLATE.format(
        transcript=transcript,
        history=history_text,
        question=question,
        language=language,
    )
