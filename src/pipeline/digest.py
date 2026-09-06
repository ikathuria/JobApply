"""
Weekly digest email (M23).

One SMTP send that summarizes the state of the search so you don't have to open
the dashboard: new high-score jobs, roles awaiting your review, applications due
for a follow-up, outreach follow-ups due, and company application windows opening
soon. Reuses the same SMTP sender and recipient resolution as notifications, and
no-ops gracefully without credentials.

Run: ``python main.py --digest``  (or schedule it — see .github/workflows).
"""

import json
import logging
import os
from datetime import date
from pathlib import Path

from tracker.tracker import STATUS_NEW, STATUS_QUEUED, get_jobs, list_followups_due
from pipeline.followups import stale_applications

logger = logging.getLogger(__name__)

_SETTINGS_PATH = Path("config/settings.yaml")
_CALENDAR_PATH = Path("config/recruiting_calendar.json")


def _recipient() -> str:
    to = ""
    try:
        import yaml
        settings = yaml.safe_load(_SETTINGS_PATH.read_text(encoding="utf-8")) or {}
        to = (settings.get("notifications", {}) or {}).get("email_to", "") or ""
    except Exception:
        to = ""
    return (to or os.environ.get("SMTP_USER") or os.environ.get("GMAIL_ADDRESS") or "").strip()


def _upcoming_windows(today: date, within_days: int = 30) -> list[str]:
    try:
        cal = json.loads(_CALENDAR_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    out = []
    for comp in cal.get("companies", []):
        opens_raw = comp.get("opens")
        name = comp.get("name", "")
        if not name:
            continue
        try:
            opens = date.fromisoformat(opens_raw) if opens_raw else None
        except (TypeError, ValueError):
            opens = None
        if opens and 0 <= (opens - today).days <= within_days:
            out.append(f"{name} — opens {opens.isoformat()} (in {(opens - today).days}d)")
        elif comp.get("rolling") and not opens:
            continue
    return out


def build_digest(conn, today: date | None = None) -> dict:
    """Compose the digest. Returns {subject, body, sections} — sections is a dict
    of the raw counts/lists so it's easy to test."""
    today = today or date.today()

    new_jobs = [dict(j) for j in get_jobs(conn, status=STATUS_NEW, limit=10)]
    queued = [dict(j) for j in get_jobs(conn, status=STATUS_QUEUED, limit=200)]
    stale = stale_applications(conn, days=7, today=today)
    try:
        outreach_due = [dict(r) for r in list_followups_due(conn, today.isoformat())]
    except Exception:
        outreach_due = []
    windows = _upcoming_windows(today)

    lines = [f"JobApply weekly digest — {today.isoformat()}", ""]

    lines.append(f"● {len(new_jobs)} new high-score role(s) to review:")
    for j in new_jobs[:10]:
        lines.append(f"   [{(j.get('score') or 0):.2f}] {j.get('title')} @ {j.get('company') or 'N/A'}")
    lines.append("")

    lines.append(f"● {len(queued)} tailored role(s) awaiting your approval.")
    lines.append("")

    lines.append(f"● {len(stale)} application(s) with no response in 7+ days (consider a nudge):")
    for j in stale[:10]:
        d = j.get("days_since_applied")
        ago = f"{d}d ago" if d is not None else "unknown"
        lines.append(f"   {j.get('title')} @ {j.get('company') or 'N/A'} — applied {ago}")
    lines.append("")

    if outreach_due:
        lines.append(f"● {len(outreach_due)} outreach follow-up(s) due.")
        lines.append("")

    if windows:
        lines.append("● Application windows opening soon:")
        for w in windows:
            lines.append(f"   {w}")
        lines.append("")

    lines.append("— Open the dashboard (make local) to act on these.")

    subject = (
        f"[JobApply] Weekly digest — {len(new_jobs)} new, "
        f"{len(queued)} to review, {len(stale)} to follow up"
    )
    return {
        "subject": subject,
        "body": "\n".join(lines),
        "sections": {
            "new": new_jobs, "queued": queued, "stale": stale,
            "outreach_due": outreach_due, "windows": windows,
        },
    }


def send_digest(conn, today: date | None = None) -> bool:
    """Build + send the digest. Returns True on send, False otherwise."""
    to = _recipient()
    if not to:
        logger.error("Digest not sent — no recipient (set notifications.email_to or SMTP_USER).")
        return False
    digest = build_digest(conn, today=today)
    from pipeline.email_sender import send_email
    ok = send_email(to, digest["subject"], digest["body"])
    logger.info(f"Digest to {to}: sent={ok}")
    return bool(ok)
