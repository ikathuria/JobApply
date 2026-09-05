"""
Send outreach emails over SMTP.

Provider-agnostic: configure any mailbox via the ``SMTP_*`` env vars.

    SMTP_HOST      SMTP server hostname        (default: smtp.gmail.com)
    SMTP_PORT      submission port             (default: 465)
    SMTP_USER      login username / address    (default: GMAIL_ADDRESS)
    SMTP_PASSWORD  login password              (default: GMAIL_APP_PASSWORD)
    SMTP_FROM      From: address               (default: SMTP_USER)
    SMTP_SECURITY  "ssl" | "starttls"          (default: inferred from port —
                                                587 → starttls, else ssl)

For backward compatibility, GMAIL_ADDRESS / GMAIL_APP_PASSWORD are still read
when the SMTP_USER / SMTP_PASSWORD vars are unset, and the defaults point at
Gmail. Sending is best-effort: any failure is logged and returns False so
callers never crash the request path.
"""

import logging
import os
import smtplib
from email.message import EmailMessage

logger = logging.getLogger(__name__)

DEFAULT_HOST = "smtp.gmail.com"
DEFAULT_PORT = 465


def _config():
    """Resolve SMTP settings from env, with Gmail-compatible fallbacks."""
    user = (os.getenv("SMTP_USER") or os.getenv("GMAIL_ADDRESS") or "").strip()
    password = (os.getenv("SMTP_PASSWORD") or os.getenv("GMAIL_APP_PASSWORD") or "").strip()
    host = (os.getenv("SMTP_HOST") or DEFAULT_HOST).strip()
    try:
        port = int(os.getenv("SMTP_PORT") or DEFAULT_PORT)
    except ValueError:
        port = DEFAULT_PORT
    sender = (os.getenv("SMTP_FROM") or user).strip()
    security = (os.getenv("SMTP_SECURITY") or "").strip().lower()
    if security not in ("ssl", "starttls"):
        security = "starttls" if port == 587 else "ssl"
    return host, port, user, password, sender, security


def send_email(to: str, subject: str, body: str) -> bool:
    """Send a plain-text email. Returns True on success, False on any failure
    (missing creds, SMTP error, etc.) — the error is logged, not raised."""
    host, port, user, password, sender, security = _config()
    if not user or not password:
        logger.error(
            "SMTP credentials not set — set SMTP_USER / SMTP_PASSWORD "
            "(or GMAIL_ADDRESS / GMAIL_APP_PASSWORD)."
        )
        return False
    if not to:
        logger.error("send_email called with no recipient.")
        return False

    msg = EmailMessage()
    msg["From"] = sender or user
    msg["To"] = to
    msg["Subject"] = subject or ""
    msg.set_content(body or "")

    try:
        if security == "starttls":
            with smtplib.SMTP(host, port, timeout=30) as smtp:
                smtp.starttls()
                smtp.login(user, password)
                smtp.send_message(msg)
        else:
            with smtplib.SMTP_SSL(host, port, timeout=30) as smtp:
                smtp.login(user, password)
                smtp.send_message(msg)
        logger.info(f"Email sent to {to}: {subject!r}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email to {to} via {host}:{port}: {e}")
        return False
