"""
Unit tests for pipeline.email_sender with smtplib mocked (no real email sent).
"""

from unittest.mock import MagicMock, patch

import pipeline.email_sender as es


def _set_creds(monkeypatch):
    monkeypatch.setenv("GMAIL_ADDRESS", "me@gmail.com")
    monkeypatch.setenv("GMAIL_APP_PASSWORD", "app-password-123")


def test_send_success(monkeypatch):
    _set_creds(monkeypatch)
    smtp = MagicMock()
    with patch.object(es.smtplib, "SMTP_SSL") as ssl:
        ssl.return_value.__enter__.return_value = smtp
        ok = es.send_email("to@x.com", "Hi", "Body")
    assert ok is True
    smtp.login.assert_called_once_with("me@gmail.com", "app-password-123")
    sent_msg = smtp.send_message.call_args.args[0]
    assert sent_msg["To"] == "to@x.com"
    assert sent_msg["From"] == "me@gmail.com"
    assert sent_msg["Subject"] == "Hi"


def test_missing_credentials_returns_false(monkeypatch):
    monkeypatch.delenv("GMAIL_ADDRESS", raising=False)
    monkeypatch.delenv("GMAIL_APP_PASSWORD", raising=False)
    with patch.object(es.smtplib, "SMTP_SSL") as ssl:
        assert es.send_email("to@x.com", "Hi", "Body") is False
        ssl.assert_not_called()  # never even attempts a connection


def test_missing_recipient_returns_false(monkeypatch):
    _set_creds(monkeypatch)
    with patch.object(es.smtplib, "SMTP_SSL") as ssl:
        assert es.send_email("", "Hi", "Body") is False
        ssl.assert_not_called()


def test_smtp_error_is_swallowed(monkeypatch):
    _set_creds(monkeypatch)
    with patch.object(es.smtplib, "SMTP_SSL", side_effect=OSError("connection refused")):
        assert es.send_email("to@x.com", "Hi", "Body") is False
