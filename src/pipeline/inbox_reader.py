"""
Read recent messages from an IMAP mailbox (read-only).

Configure via env (falls back to the SMTP_* / GMAIL_* creds already used for
sending, since it's usually the same mailbox):

    IMAP_HOST      IMAP server hostname   (default: derived from SMTP_HOST, else imap.gmail.com)
    IMAP_PORT      IMAP SSL port          (default: 993)
    IMAP_USER      login                  (default: SMTP_USER / GMAIL_ADDRESS)
    IMAP_PASSWORD  password               (default: SMTP_PASSWORD / GMAIL_APP_PASSWORD)
    IMAP_MAILBOX   folder to read         (default: INBOX)

This never deletes, moves, or marks anything read — it only fetches. Any failure
is logged and yields an empty list so the scanner degrades gracefully.
"""

import email
import imaplib
import logging
import os
from datetime import datetime, timedelta, timezone
from email.header import decode_header
from email.utils import parsedate_to_datetime

logger = logging.getLogger(__name__)

DEFAULT_IMAP_PORT = 993


def _config():
    user = (os.getenv("IMAP_USER") or os.getenv("SMTP_USER")
            or os.getenv("GMAIL_ADDRESS") or "").strip()
    password = (os.getenv("IMAP_PASSWORD") or os.getenv("SMTP_PASSWORD")
                or os.getenv("GMAIL_APP_PASSWORD") or "").strip()
    host = (os.getenv("IMAP_HOST") or "").strip()
    if not host:
        smtp_host = (os.getenv("SMTP_HOST") or "").strip()
        # smtp.example.com → imap.example.com; mail.example.com stays mail.example.com
        if smtp_host.startswith("smtp."):
            host = "imap." + smtp_host[len("smtp."):]
        elif smtp_host:
            host = smtp_host
        else:
            host = "imap.gmail.com"
    try:
        port = int(os.getenv("IMAP_PORT") or DEFAULT_IMAP_PORT)
    except ValueError:
        port = DEFAULT_IMAP_PORT
    mailbox = (os.getenv("IMAP_MAILBOX") or "INBOX").strip()
    return host, port, user, password, mailbox


def _decode(value: str) -> str:
    """Decode an RFC 2047 encoded header into a plain string."""
    if not value:
        return ""
    parts = []
    for text, enc in decode_header(value):
        if isinstance(text, bytes):
            try:
                parts.append(text.decode(enc or "utf-8", errors="replace"))
            except (LookupError, TypeError):
                parts.append(text.decode("utf-8", errors="replace"))
        else:
            parts.append(text)
    return "".join(parts)


def _body_text(msg: email.message.Message) -> str:
    """Best-effort plain-text body (prefers text/plain, falls back to any text)."""
    if msg.is_multipart():
        plain, other = "", ""
        for part in msg.walk():
            ctype = part.get_content_type()
            if part.get("Content-Disposition", "").startswith("attachment"):
                continue
            if ctype not in ("text/plain", "text/html"):
                continue
            try:
                payload = part.get_payload(decode=True)
                if payload is None:
                    continue
                text = payload.decode(part.get_content_charset() or "utf-8", errors="replace")
            except Exception:
                continue
            if ctype == "text/plain" and not plain:
                plain = text
            elif not other:
                other = text
        return plain or other
    try:
        payload = msg.get_payload(decode=True)
        if payload is None:
            return str(msg.get_payload())
        return payload.decode(msg.get_content_charset() or "utf-8", errors="replace")
    except Exception:
        return ""


def fetch_recent(limit: int = 40, days: int = 30) -> list[dict]:
    """Fetch up to ``limit`` messages from the last ``days`` days.

    Returns a list of ``{from, subject, body, date}`` dicts (newest first).
    Returns [] on any error or missing credentials.
    """
    host, port, user, password, mailbox = _config()
    if not user or not password:
        logger.error("IMAP credentials not set — set IMAP_USER / IMAP_PASSWORD "
                     "(or reuse SMTP_USER / SMTP_PASSWORD).")
        return []

    try:
        imap = imaplib.IMAP4_SSL(host, port, timeout=30)
    except Exception as e:
        logger.error(f"IMAP connect failed ({host}:{port}): {e}")
        return []

    messages: list[dict] = []
    try:
        imap.login(user, password)
        imap.select(mailbox, readonly=True)
        since = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%d-%b-%Y")
        status, data = imap.search(None, f'(SINCE {since})')
        if status != "OK":
            return []
        ids = data[0].split()
        for num in reversed(ids[-limit:]):  # newest first
            status, msg_data = imap.fetch(num, "(RFC822)")
            if status != "OK" or not msg_data or not msg_data[0]:
                continue
            msg = email.message_from_bytes(msg_data[0][1])
            date = None
            try:
                if msg.get("Date"):
                    date = parsedate_to_datetime(msg["Date"])
            except (TypeError, ValueError):
                date = None
            messages.append({
                "from": _decode(msg.get("From", "")),
                "subject": _decode(msg.get("Subject", "")),
                "body": _body_text(msg),
                "date": date.isoformat() if date else "",
            })
    except Exception as e:
        logger.error(f"IMAP fetch failed: {e}")
    finally:
        try:
            imap.logout()
        except Exception:
            pass
    return messages
