"""
Generates a tailored interview-prep pack for a specific job using the configured
LLM provider (Interview Prep Section — M9).

Grounded in Ishani's REAL profile (same no-fabrication discipline as the resume
tailoring): the question talking-points must draw on her actual experience and
projects, never invented ones.
"""

import json
import logging

from pipeline.llm_client import complete
from pipeline.resume_tailor import _load_profile, _profile_text

logger = logging.getLogger(__name__)


SYSTEM_PROMPT_TEMPLATE = """You are an expert interview coach preparing a candidate \
for an AI/ML interview. Produce a focused, practical prep pack.

CANDIDATE PROFILE:
{profile_text}

INSTRUCTIONS:
- Ground every "talking_points" entry in the candidate's REAL experience/projects above. NEVER invent experience.
- "topics_to_review": concrete technical areas implied by the job description, prioritized for this candidate.
- Question banks: realistic for this role/level; 2-4 talking points each, from the candidate's real work.
  - "behavioral": STAR-style, tied to their actual experience (AWS, research, projects).
  - "technical": role-specific ML/AI/CS domain questions.
  - "system_design": ML/software system-design prompts appropriate to the level.
- "questions_to_ask": smart questions the candidate should ask the interviewer.
- "checklist": short night-before / day-of reminders.

Respond ONLY with valid JSON matching this exact schema (no markdown, no code fences):
{{
  "snapshot": "2-3 sentences: what the team/product does and why the candidate fits",
  "topics_to_review": ["string"],
  "questions": {{
    "behavioral": [{{"q": "string", "talking_points": ["string"]}}],
    "technical": [{{"q": "string", "talking_points": ["string"]}}],
    "system_design": [{{"q": "string", "talking_points": ["string"]}}]
  }},
  "questions_to_ask": ["string"],
  "checklist": ["string"]
}}"""


def _strip_fences(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()
    return raw


def generate_prep(job: dict, jd_text: str, profile: dict | None = None) -> dict | None:
    """Generate a structured interview-prep pack for `job`. Returns a dict, or
    None on failure. `jd_text` is the job description (stored or freshly fetched)."""
    profile = profile or _load_profile()
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(profile_text=_profile_text(profile))

    user_message = f"""Prepare interview prep for this position:

COMPANY: {job.get('company', 'Unknown')}
ROLE: {job.get('title', 'Unknown')}
LOCATION: {job.get('location', '')}

JOB DESCRIPTION:
{(jd_text or '')[:6000]}"""

    raw = ""
    try:
        raw = complete(system_prompt, user_message, max_tokens=4000)
        pack = json.loads(_strip_fences(raw))
        # light shape guard — ensure the buckets exist so the UI never crashes
        pack.setdefault("snapshot", "")
        pack.setdefault("topics_to_review", [])
        q = pack.setdefault("questions", {})
        for bucket in ("behavioral", "technical", "system_design"):
            q.setdefault(bucket, [])
        pack.setdefault("questions_to_ask", [])
        pack.setdefault("checklist", [])
        logger.info(f"Generated interview prep for '{job.get('title')}' @ '{job.get('company')}'")
        return pack
    except json.JSONDecodeError as e:
        logger.error(f"Interview prep: invalid JSON: {e}\nRaw (first 500):\n{raw[:500]}")
        return None
    except Exception as e:
        logger.error(f"Interview prep generation error: {e}")
        return None
