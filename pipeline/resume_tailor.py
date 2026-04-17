"""
Generates a tailored resume JSON for a specific job using the configured LLM provider.
Switch provider in config/settings.yaml (llm.provider: gemini | anthropic).
"""

import json
import logging
from pathlib import Path

from pipeline.llm_client import complete

logger = logging.getLogger(__name__)

PROFILE_PATH = Path("config/profile.json")


def _load_profile() -> dict:
    with open(PROFILE_PATH) as f:
        return json.load(f)


def _profile_text(profile: dict) -> str:
    lines = [
        f"Name: {profile['name']}",
        f"Email: {profile['email']}",
        f"Phone: {profile['phone']}",
        f"Location: {profile['location']}",
        "",
        "=== EDUCATION ===",
    ]
    for edu in profile.get("education", []):
        lines.append(f"- {edu['degree']} @ {edu['school']} ({edu['start']}-{edu['end']}, GPA {edu['gpa']})")

    lines += ["", "=== EXPERIENCE ==="]
    for exp in profile.get("experience", []):
        lines.append(f"\n{exp['title']} @ {exp['company']} ({exp['start']}-{exp['end']})")
        for b in exp.get("bullets", []):
            lines.append(f"  - {b}")

    lines += ["", "=== PROJECTS ==="]
    for proj in profile.get("projects", []):
        lines.append(f"\n{proj['name']}")
        for b in proj.get("bullets", []):
            lines.append(f"  - {b}")

    lines += ["", "=== SKILLS ==="]
    for cat, items in profile.get("skills", {}).items():
        lines.append(f"  {cat}: {', '.join(items)}")

    lines += ["", "=== CERTIFICATIONS ==="]
    for cert in profile.get("certifications", []):
        lines.append(f"  - {cert}")

    lines += ["", "=== PUBLICATIONS ==="]
    for pub in profile.get("publications", []):
        lines.append(f"  - {pub}")

    return "\n".join(lines)


SYSTEM_PROMPT_TEMPLATE = """You are an expert technical resume writer helping a candidate tailor their resume for AI/ML internship roles.

CANDIDATE PROFILE:
{profile_text}

INSTRUCTIONS:
- Reorder and reframe the candidate's REAL experience to best match the job description
- NEVER fabricate skills, tools, or experiences not present in the profile
- Emphasize most-relevant experience bullets; you may omit less-relevant ones to keep focus
- Keep bullet points concise, metric-driven, and action-verb led
- Select the 2-3 most relevant projects for this specific role
- For skills, promote categories most relevant to the JD to the top
- Write a 2-sentence professional summary tailored to the specific role
- "why_fit" is 1-2 sentences for use as a cover letter hook; make it specific to the company/role

Respond ONLY with valid JSON matching this exact schema (no markdown, no code fences):
{{
  "summary": "string",
  "experience": [
    {{
      "company": "string",
      "title": "string",
      "start": "string",
      "end": "string",
      "bullets": ["string"]
    }}
  ],
  "projects": [
    {{
      "name": "string",
      "bullets": ["string"]
    }}
  ],
  "skills": {{
    "category_name": ["skill1", "skill2"]
  }},
  "why_fit": "string"
}}"""


def tailor_resume(job: dict, jd_text: str) -> dict | None:
    """
    Generate a tailored resume for the given job using the configured LLM.
    Returns tailored resume dict, or None on failure.
    """
    profile = _load_profile()
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(profile_text=_profile_text(profile))

    user_message = f"""Please tailor the resume for this position:

COMPANY: {job.get('company', 'Unknown')}
ROLE: {job.get('title', 'Unknown')}
JOB URL: {job.get('url', '')}

JOB DESCRIPTION:
{jd_text[:6000]}"""

    try:
        raw = complete(system_prompt, user_message, max_tokens=4000)

        # Strip markdown code fences if the model wraps output
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()

        tailored = json.loads(raw)

        # Inject static fields the LLM doesn't change
        tailored.update({
            "name":           profile["name"],
            "email":          profile["email"],
            "phone":          profile["phone"],
            "location":       profile["location"],
            "linkedin":       profile["linkedin"],
            "github":         profile["github"],
            "portfolio":      profile["portfolio"],
            "education":      profile["education"],
            "certifications": profile["certifications"],
            "publications":   profile["publications"],
        })

        logger.info(f"Tailored resume for '{job.get('title')}' @ '{job.get('company')}'")
        return tailored

    except json.JSONDecodeError as e:
        logger.error(f"LLM returned invalid JSON: {e}\nRaw response (first 500 chars):\n{raw[:500]}")
        return None
    except Exception as e:
        logger.error(f"Resume tailoring error: {e}")
        return None
