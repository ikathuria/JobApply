"""
Send outreach emails from Ishani's Gmail via SMTP.

Uses an App Password (Google Account → Security → App Passwords) over
``smtplib.SMTP_SSL`` — no OAuth2 dance. Credentials come from the GMAIL_ADDRESS
and GMAIL_APP_PASSWORD env vars. Sending is best-effort: any failure is logged
and returns False so callers never crash the request path.
"""

import logging
import os
import smtplib
from email.message import EmailMessage

logger = logging.getLogger(__name__)

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 465


def send_email(to: str, subject: str, body: str) -> bool:
    """Send a plain-text email. Returns True on success, False on any failure
    (missing creds, SMTP error, etc.) — the error is logged, not raised."""
    addr = os.getenv("GMAIL_ADDRESS", "").strip()
    password = os.getenv("GMAIL_APP_PASSWORD", "").strip()
    if not addr or not password:
        logger.error("GMAIL_ADDRESS / GMAIL_APP_PASSWORD not set — cannot send email.")
        return False
    if not to:
        logger.error("send_email called with no recipient.")
        return False

    msg = EmailMessage()
    msg["From"] = addr
    msg["To"] = to
    msg["Subject"] = subject or ""
    msg.set_content(body or "")

    try:
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=30) as smtp:
            smtp.login(addr, password)
            smtp.send_message(msg)
        logger.info(f"Email sent to {to}: {subject!r}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email to {to}: {e}")
        return False
