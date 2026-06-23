"""
Generates personalized cold-outreach emails and referral asks using the
configured LLM provider (Groq by default — see pipeline/llm_client.py).

Two flavours, selected by ``email_type``:
- "cold"     → to a recruiter / HR contact: introduce, show fit, ask for 15 min
               or a pointer to the right person. Max ~200 words.
- "referral" → to a current employee (engineer / PM): warmer, asks for a referral
               or intro to the hiring team. Max ~150 words.

``generate_cold_email`` returns ``{"subject": str, "body": str}``.
"""

import json
import logging
from pathlib import Path

from pipeline.llm_client import complete

logger = logging.getLogger(__name__)

PROFILE_PATH = Path("config/profile.json")

COLD = "cold"
REFERRAL = "referral"


def _load_profile() -> dict:
    with open(PROFILE_PATH) as f:
        return json.load(f)


def _candidate_context(profile: dict) -> str:
    """Compact, factual blurb the model uses — never fabricate beyond this."""
    lines = [f"Name: {profile.get('name', '')}"]

    edu = (profile.get("education") or [{}])[0]
    if edu:
        wa = profile.get("work_authorization", {})
        grad = wa.get("expected_graduation", "")
        gpa = wa.get("gpa") or edu.get("gpa", "")
        lines.append(
            f"Current: {edu.get('degree', '')} @ {edu.get('school', '')}"
            + (f", GPA {gpa}" if gpa else "")
            + (f", graduating {grad}" if grad else "")
        )

    exps = profile.get("experience") or []
    if exps:
        lines.append("Experience:")
        for exp in exps[:3]:
            lines.append(f"  - {exp.get('title', '')} @ {exp.get('company', '')}")

    skills = profile.get("skills") or {}
    if skills:
        flat = [s for items in skills.values() for s in items][:12]
        lines.append("Key skills: " + ", ".join(flat))

    projects = profile.get("projects") or []
    if projects:
        lines.append("Notable projects: " + ", ".join(p.get("name", "") for p in projects[:3]))

    links = []
    if profile.get("linkedin"):
        links.append(profile["linkedin"])
    if profile.get("portfolio"):
        links.append(profile["portfolio"])
    if links:
        lines.append("Links: " + " | ".join(links))

    return "\n".join(lines)


_COLD_SYSTEM = """You write concise, genuine cold outreach emails from a student seeking an AI/ML
internship to a recruiter or HR contact.

CANDIDATE (use only these facts — never invent experience, schools, or skills):
{candidate}

RULES:
- Open by naming the SPECIFIC role and company (if a role is given).
- 2-3 sentences on the candidate's most relevant background for an AI/ML role.
- One clear, low-friction ask: 15 minutes to connect, OR a pointer to the right contact.
- Warm and direct. NO generic filler ("I am reaching out to express my interest..."), NO buzzword soup, NO flattery.
- Under 200 words total. First person. Sign off with the candidate's name.

Respond ONLY with JSON, no code fences:
{{"subject": "short specific subject line", "body": "full email body with greeting and sign-off"}}"""


_REFERRAL_SYSTEM = """You write short, warm referral-request emails from a student seeking an AI/ML
internship to a CURRENT EMPLOYEE at a target company (an engineer, PM, or researcher — not a recruiter).

CANDIDATE (use only these facts — never invent experience, schools, or skills):
{candidate}

RULES:
- Acknowledge you know they're busy; be respectful of their time.
- 1-2 sentences on why the candidate is a strong fit for AI/ML work at THIS company.
- Reference any shared context if provided (same school, shared interest).
- Clear ask: would they be willing to refer the candidate, or intro them to the hiring team?
- Under 150 words total. First person. Sign off with the candidate's name.

Respond ONLY with JSON, no code fences:
{{"subject": "short specific subject line", "body": "full email body with greeting and sign-off"}}"""


def _parse(raw: str) -> dict:
    """Parse the LLM response into {subject, body}, tolerating code fences and
    a plain 'Subject: ...\\n\\n<body>' fallback."""
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()

    try:
        # strict=False tolerates literal newlines inside string values — LLMs
        # routinely emit pretty-printed JSON with real line breaks in the body,
        # which a strict parse would reject.
        data = json.loads(text, strict=False)
        subject = (data.get("subject") or "").strip()
        body = (data.get("body") or "").strip()
        if subject or body:
            return {"subject": subject, "body": body}
    except json.JSONDecodeError:
        pass

    # Fallback: "Subject: ...\n\n<body>"
    subject = ""
    body = raw.strip()
    for line in raw.splitlines():
        if line.lower().startswith("subject:"):
            subject = line.split(":", 1)[1].strip()
            body = raw.split(line, 1)[1].strip()
            break
    return {"subject": subject, "body": body}


def generate_cold_email(
    recruiter: dict,
    job: dict | None,
    profile: dict | None = None,
    email_type: str = COLD,
) -> dict:
    """Generate a personalized outreach email.

    Args:
        recruiter: dict with at least ``name``; optional ``company``, ``title``.
        job: dict with ``title`` + ``company`` (or None for a general intro).
        profile: candidate profile dict; loaded from config/profile.json if None.
        email_type: ``"cold"`` (recruiter/HR) or ``"referral"`` (employee).

    Returns ``{"subject": str, "body": str}``.
    """
    profile = profile or _load_profile()
    system_tmpl = _REFERRAL_SYSTEM if email_type == REFERRAL else _COLD_SYSTEM
    system_prompt = system_tmpl.format(candidate=_candidate_context(profile))

    job = job or {}
    company = (recruiter.get("company") or job.get("company") or "the company").strip()
    role = (job.get("title") or "").strip()
    audience = "current employee" if email_type == REFERRAL else "recruiter / HR contact"

    user_message = f"""Write the email.

RECIPIENT ({audience}):
  Name: {recruiter.get('name', '')}
  Title: {recruiter.get('title', '') or 'unknown'}
  Company: {company}

TARGET ROLE: {role or 'AI/ML internship (no specific posting — general interest)'}
"""

    raw = complete(system_prompt, user_message, max_tokens=500)
    result = _parse(raw)
    logger.info(
        f"Generated {email_type} email for {recruiter.get('name', '?')} @ {company}"
    )
    return result
