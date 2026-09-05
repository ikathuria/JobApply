"""
Unit tests for pipeline.email_sender with smtplib mocked (no real email sent).

These tests are hermetic: they clear every SMTP_* / GMAIL_* env var first so a
developer's real ``.env`` (loaded by ``api.main`` via ``load_dotenv()`` when
another test imports it) can't leak in and change the resolved config.
"""

from unittest.mock import MagicMock, patch

import pytest

import pipeline.email_sender as es

_ENV_VARS = (
    "SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASSWORD",
    "SMTP_FROM", "SMTP_SECURITY", "GMAIL_ADDRESS", "GMAIL_APP_PASSWORD",
)


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    """Start every test from a known-empty SMTP/Gmail environment."""
    for var in _ENV_VARS:
        monkeypatch.delenv(var, raising=False)


def _set_gmail(monkeypatch):
    monkeypatch.setenv("GMAIL_ADDRESS", "me@gmail.com")
    monkeypatch.setenv("GMAIL_APP_PASSWORD", "app-password-123")


def test_send_success_gmail_ssl(monkeypatch):
    """Legacy Gmail vars → SSL on the default port 465."""
    _set_gmail(monkeypatch)
    smtp = MagicMock()
    with patch.object(es.smtplib, "SMTP_SSL") as ssl, \
            patch.object(es.smtplib, "SMTP") as plain:
        ssl.return_value.__enter__.return_value = smtp
        ok = es.send_email("to@x.com", "Hi", "Body")
    assert ok is True
    ssl.assert_called_once()
    assert ssl.call_args.args[:2] == ("smtp.gmail.com", 465)
    plain.assert_not_called()  # no STARTTLS path
    smtp.login.assert_called_once_with("me@gmail.com", "app-password-123")
    sent_msg = smtp.send_message.call_args.args[0]
    assert sent_msg["To"] == "to@x.com"
    assert sent_msg["From"] == "me@gmail.com"
    assert sent_msg["Subject"] == "Hi"


def test_send_success_custom_ssl(monkeypatch):
    """Generic SMTP_* vars on an SSL port, with a distinct From address."""
    monkeypatch.setenv("SMTP_HOST", "mail.example.net")
    monkeypatch.setenv("SMTP_PORT", "465")
    monkeypatch.setenv("SMTP_USER", "ishani@example.net")
    monkeypatch.setenv("SMTP_PASSWORD", "secret")
    monkeypatch.setenv("SMTP_FROM", "hello@example.net")
    smtp = MagicMock()
    with patch.object(es.smtplib, "SMTP_SSL") as ssl:
        ssl.return_value.__enter__.return_value = smtp
        ok = es.send_email("to@x.com", "Hi", "Body")
    assert ok is True
    assert ssl.call_args.args[:2] == ("mail.example.net", 465)
    smtp.login.assert_called_once_with("ishani@example.net", "secret")
    assert smtp.send_message.call_args.args[0]["From"] == "hello@example.net"


def test_send_success_starttls(monkeypatch):
    """Port 587 → STARTTLS path (plain SMTP + starttls())."""
    monkeypatch.setenv("SMTP_HOST", "smtp.example.net")
    monkeypatch.setenv("SMTP_PORT", "587")
    monkeypatch.setenv("SMTP_USER", "ishani@example.net")
    monkeypatch.setenv("SMTP_PASSWORD", "secret")
    smtp = MagicMock()
    with patch.object(es.smtplib, "SMTP") as plain, \
            patch.object(es.smtplib, "SMTP_SSL") as ssl:
        plain.return_value.__enter__.return_value = smtp
        ok = es.send_email("to@x.com", "Hi", "Body")
    assert ok is True
    ssl.assert_not_called()
    assert plain.call_args.args[:2] == ("smtp.example.net", 587)
    smtp.starttls.assert_called_once()
    smtp.login.assert_called_once_with("ishani@example.net", "secret")
    # From falls back to SMTP_USER when SMTP_FROM is unset
    assert smtp.send_message.call_args.args[0]["From"] == "ishani@example.net"


def test_security_override_forces_starttls(monkeypatch):
    """Explicit SMTP_SECURITY=starttls wins over the port-based default."""
    monkeypatch.setenv("SMTP_USER", "ishani@example.net")
    monkeypatch.setenv("SMTP_PASSWORD", "secret")
    monkeypatch.setenv("SMTP_PORT", "465")
    monkeypatch.setenv("SMTP_SECURITY", "starttls")
    smtp = MagicMock()
    with patch.object(es.smtplib, "SMTP") as plain, \
            patch.object(es.smtplib, "SMTP_SSL") as ssl:
        plain.return_value.__enter__.return_value = smtp
        assert es.send_email("to@x.com", "Hi", "Body") is True
    ssl.assert_not_called()
    smtp.starttls.assert_called_once()


def test_missing_credentials_returns_false(monkeypatch):
    with patch.object(es.smtplib, "SMTP_SSL") as ssl, \
            patch.object(es.smtplib, "SMTP") as plain:
        assert es.send_email("to@x.com", "Hi", "Body") is False
        ssl.assert_not_called()  # never even attempts a connection
        plain.assert_not_called()


def test_missing_recipient_returns_false(monkeypatch):
    _set_gmail(monkeypatch)
    with patch.object(es.smtplib, "SMTP_SSL") as ssl:
        assert es.send_email("", "Hi", "Body") is False
        ssl.assert_not_called()


def test_smtp_error_is_swallowed(monkeypatch):
    _set_gmail(monkeypatch)
    with patch.object(es.smtplib, "SMTP_SSL", side_effect=OSError("connection refused")):
        assert es.send_email("to@x.com", "Hi", "Body") is False


def test_invalid_port_falls_back_to_default(monkeypatch):
    _set_gmail(monkeypatch)
    monkeypatch.setenv("SMTP_PORT", "not-a-number")
    smtp = MagicMock()
    with patch.object(es.smtplib, "SMTP_SSL") as ssl:
        ssl.return_value.__enter__.return_value = smtp
        assert es.send_email("to@x.com", "Hi", "Body") is True
    assert ssl.call_args.args[1] == 465
