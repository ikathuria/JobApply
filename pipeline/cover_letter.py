"""
Generates a tailored cover letter using the configured LLM provider.
Switch provider in config/settings.yaml (llm.provider: gemini | anthropic).
"""

import logging

from pipeline.llm_client import complete

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an expert career coach writing concise, compelling cover letters for AI/ML internship positions.

Write in first person, professional but not stiff. Keep it to 3 short paragraphs:
1. Hook — what excites you about this specific company/role (use why_fit from context)
2. Evidence — 2–3 concrete achievements from your experience most relevant to this JD
3. Close — brief expression of enthusiasm and call to action

Do NOT:
- Use generic filler phrases ("I am writing to express my interest...")
- Repeat the resume verbatim
- Exceed 250 words

Return ONLY the plain cover letter text, no subject line, no salutation header, no JSON."""


def generate_cover_letter(job: dict, jd_text: str, why_fit: str) -> str:
    """
    Generate a cover letter for the given job.
    why_fit comes from the tailored resume output.
    Returns cover letter as plain text, or empty string on failure.
    """
    user_message = f"""Write a cover letter for this internship application.

COMPANY: {job.get('company', 'Unknown')}
ROLE: {job.get('title', 'Unknown')}

SPECIFIC FIT NOTE (use as your hook): {why_fit}

JOB DESCRIPTION HIGHLIGHTS:
{jd_text[:3000]}"""

    try:
        letter = complete(SYSTEM_PROMPT, user_message, max_tokens=600)
        logger.info(f"Cover letter generated for '{job.get('title')}' @ '{job.get('company')}'")
        return letter.strip()
    except Exception as e:
        logger.error(f"Cover letter generation error: {e}")
        return ""
