"""
Shared status-change email notifications.

Both the API (on a manual status patch) and the inbox scanner (on an
auto-detected reply) route through :func:`notify_status_change` so the toggle
logic, recipient resolution, and message format live in one place.

Sending is best-effort: it returns True/False and never raises, so a failed
send never breaks the caller's path.
"""

import logging
import os

logger = logging.getLogger(__name__)

# Status → the settings toggle that gates a notification email on that transition.
NOTIFY_STATUS = {"offer": "on_offer", "interview": "on_interview", "oa": "on_oa"}


def _recipient(notif: dict, default_to: str | None) -> str:
    return (
        notif.get("email_to")
        or default_to
        or os.environ.get("SMTP_USER")
        or os.environ.get("GMAIL_ADDRESS")
        or ""
    ).strip()


def notify_status_change(
    job: dict, new_status: str, settings: dict | None, default_to: str | None = None
) -> bool:
    """Email a notification when a job reaches a milestone status.

    Args:
        job: the job row (dict) — used for company/title/url in the message.
        new_status: the status just transitioned into.
        settings: the parsed settings.yaml dict (its ``notifications`` block gates
            which transitions email and to whom).
        default_to: fallback recipient if ``notifications.email_to`` is unset.

    Returns True if an email was sent, False otherwise (toggle off, no recipient,
    non-milestone status, or send failure).
    """
    key = NOTIFY_STATUS.get(new_status)
    if not key:
        return False
    notif = (settings or {}).get("notifications", {}) or {}
    if not notif.get(key):
        return False
    to = _recipient(notif, default_to)
    if not to:
        logger.warning("Status notification skipped — set notifications.email_to or SMTP_USER")
        return False

    company = job.get("company") or "a company"
    title = job.get("title") or "a role"
    subject = f"[JobApply] {company} → {new_status.upper()}: {title}"
    body = (
        f"Status update: {title} @ {company} moved to {new_status.upper()}.\n\n"
        f"URL: {job.get('url', '')}\n"
    )
    try:
        from pipeline.email_sender import send_email
        ok = send_email(to, subject, body)
        logger.info(f"Status notification for job {job.get('id')} → {new_status}: sent={ok}")
        return bool(ok)
    except Exception as e:
        logger.warning(f"Status notification failed: {e}")
        return False
