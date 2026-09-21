"""
Daily reminder email (M35).

A short, action-first nudge — sent once a day — so the search keeps moving even
on busy days: what to apply to today, who to ask for a referral, and what's due
for a follow-up. Deliberately lighter than the weekly digest (M23): it's a
to-do list, not a status report. Reuses the same SMTP sender + recipient
resolution and no-ops gracefully without credentials.

Run: ``python main.py --remind``  (or schedule it — see .github/workflows or
the launchd plist under ops/).
"""

import logging
import os
from datetime import date
from pathlib import Path

from tracker.tracker import (
    STATUS_NEW, STATUS_QUEUED, STATUS_APPROVED,
    get_jobs, list_recruiters, list_followups_due,
)
from pipeline.followups import stale_applications

logger = logging.getLogger(__name__)

_SETTINGS_PATH = Path("config/settings.yaml")


def _recipient() -> str:
    to = ""
    try:
        import yaml
        settings = yaml.safe_load(_SETTINGS_PATH.read_text(encoding="utf-8")) or {}
        to = (settings.get("notifications", {}) or {}).get("email_to", "") or ""
    except Exception:
        to = ""
    return (to or os.environ.get("SMTP_USER") or os.environ.get("GMAIL_ADDRESS") or "").strip()


def _sponsor_new_jobs(conn, limit: int = 5) -> list[dict]:
    """Top new roles at known H-1B sponsors — the best candidates to apply to."""
    from pipeline.sponsorship import is_known_sponsor
    rows = [dict(j) for j in get_jobs(conn, status=STATUS_NEW, limit=300)]
    sponsors = [j for j in rows if is_known_sponsor(j.get("company") or "")]
    return sponsors[:limit]


def _uncontacted_connections(conn, limit: int = 5) -> list[dict]:
    """LinkedIn connections not yet messaged — prime referral asks."""
    out = []
    for r in list_recruiters(conn):
        rd = dict(r)
        if rd.get("source") == "linkedin" and not (rd.get("sent_count") or 0):
            out.append(rd)
        if len(out) >= limit:
            break
    return out


def build_reminder(conn, today: date | None = None) -> dict:
    """Compose the daily reminder. Returns {subject, body, sections}."""
    today = today or date.today()

    approved = [dict(j) for j in get_jobs(conn, status=STATUS_APPROVED, limit=200)]
    queued = [dict(j) for j in get_jobs(conn, status=STATUS_QUEUED, limit=200)]
    sponsor_new = _sponsor_new_jobs(conn)
    connections = _uncontacted_connections(conn)
    stale = stale_applications(conn, days=7, today=today)
    try:
        outreach_due = [dict(r) for r in list_followups_due(conn, today.isoformat())]
    except Exception:
        outreach_due = []

    lines = [f"Good morning — your JobApply nudge for {today.isoformat()}.", ""]

    # ── Apply today ──
    lines.append("APPLY TODAY")
    if approved:
        lines.append(f"● {len(approved)} approved role(s) ready to submit:")
        for j in approved[:5]:
            lines.append(f"   {j.get('title')} @ {j.get('company') or 'N/A'}")
    if queued:
        lines.append(f"● {len(queued)} tailored role(s) awaiting your review/approval.")
    if sponsor_new:
        lines.append(f"● {len(sponsor_new)} new role(s) at known H-1B sponsors worth a look:")
        for j in sponsor_new:
            lines.append(f"   [{(j.get('score') or 0):.2f}] {j.get('title')} @ {j.get('company') or 'N/A'}")
    if not (approved or queued or sponsor_new):
        lines.append("● Nothing queued — run a scrape/tailor to refill the pipeline.")
    lines.append("")

    # ── Ask for referrals ──
    lines.append("ASK FOR REFERRALS")
    if connections:
        lines.append(f"● {len(connections)} LinkedIn connection(s) not yet contacted:")
        for r in connections:
            title = r.get("title") or ""
            company = r.get("company") or "N/A"
            lines.append(f"   {r.get('name')} — {title} @ {company}".rstrip())
        lines.append("   → Outreach tab: draft the DM, send it in LinkedIn, then 'Mark as messaged'.")
    else:
        lines.append("● No un-contacted LinkedIn connections queued "
                     "(run `make outreach-linkedin ARGS=--load` to refill).")
    lines.append("")

    # ── Follow up ──
    if stale or outreach_due:
        lines.append("FOLLOW UP")
        if stale:
            lines.append(f"● {len(stale)} application(s) with no response in 7+ days:")
            for j in stale[:5]:
                d = j.get("days_since_applied")
                ago = f"{d}d ago" if d is not None else "unknown"
                lines.append(f"   {j.get('title')} @ {j.get('company') or 'N/A'} — applied {ago}")
        if outreach_due:
            lines.append(f"● {len(outreach_due)} outreach follow-up(s) due today.")
        lines.append("")

    lines.append("— Open the dashboard (make local) to act on these.")

    to_act = len(approved) + len(queued) + len(sponsor_new)
    subject = (
        f"[JobApply] Today: {to_act} to apply/review, "
        f"{len(connections)} referral ask(s), {len(stale)} to follow up"
    )
    return {
        "subject": subject,
        "body": "\n".join(lines),
        "sections": {
            "approved": approved, "queued": queued, "sponsor_new": sponsor_new,
            "connections": connections, "stale": stale, "outreach_due": outreach_due,
        },
    }


def send_reminder(conn, today: date | None = None) -> bool:
    """Build + send the daily reminder. Returns True on send, False otherwise."""
    to = _recipient()
    if not to:
        logger.error("Reminder not sent — no recipient (set notifications.email_to or SMTP_USER).")
        return False
    reminder = build_reminder(conn, today=today)
    from pipeline.email_sender import send_email
    ok = send_email(to, reminder["subject"], reminder["body"])
    logger.info(f"Daily reminder to {to}: sent={ok}")
    return bool(ok)
