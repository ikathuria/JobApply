"""
Application follow-up nudges (M22).

You already get 7-day follow-ups for *outreach* emails; this is the equivalent
for *applications* — surfacing roles you applied to a while ago that haven't
advanced, so you can send a short nudge to the recruiter (or just re-check).

``stale_applications`` is the query; ``draft_followup`` builds a short, honest
follow-up email body (template-based — no LLM, so it's free and deterministic).
"""

from datetime import date, datetime, timedelta

from tracker.tracker import STATUS_APPLIED


def _applied_on(job: dict) -> date | None:
    raw = job.get("date_applied") or job.get("updated_at") or ""
    if not raw:
        return None
    try:
        return datetime.fromisoformat(str(raw)).date()
    except ValueError:
        try:
            return date.fromisoformat(str(raw)[:10])
        except ValueError:
            return None


def stale_applications(conn, days: int = 7, today: date | None = None) -> list[dict]:
    """Jobs still at ``applied`` whose application is at least ``days`` days old,
    newest-applied first."""
    today = today or date.today()
    cutoff = today - timedelta(days=days)
    rows = conn.execute(
        "SELECT * FROM jobs WHERE status = ? ORDER BY COALESCE(date_applied, updated_at) DESC",
        (STATUS_APPLIED,),
    ).fetchall()

    out = []
    for r in rows:
        job = dict(r)
        applied = _applied_on(job)
        if applied is None or applied <= cutoff:
            job["days_since_applied"] = (today - applied).days if applied else None
            out.append(job)
    return out


def draft_followup(job: dict, profile: dict | None = None) -> dict:
    """A short, polite follow-up email for an application. Returns {subject, body}."""
    name = (profile or {}).get("name", "").strip()
    title = job.get("title") or "the role"
    company = job.get("company") or "your team"
    subject = f"Following up — {title}"
    body = (
        f"Hi,\n\n"
        f"I wanted to follow up on my application for the {title} position at {company}. "
        f"I remain very interested in the role and would welcome the chance to discuss how "
        f"my background in AI/ML could contribute to your team.\n\n"
        f"Is there any update on the status of my application, or anything further I can "
        f"provide?\n\n"
        f"Thank you for your time.\n\n"
        f"Best regards,\n{name}"
    )
    return {"subject": subject, "body": body}
