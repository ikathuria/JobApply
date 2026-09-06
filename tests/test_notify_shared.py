"""Direct tests for the shared notification helper (pipeline.notifications)."""

from pipeline import notifications as N
from pipeline import email_sender


def _capture(monkeypatch):
    sent = []
    monkeypatch.setattr(email_sender, "send_email",
                        lambda to, sub, body: sent.append((to, sub, body)) or True)
    return sent


JOB = {"id": 1, "company": "Acme", "title": "MLE", "url": "http://x"}


def test_offer_sends_when_toggle_on(monkeypatch):
    sent = _capture(monkeypatch)
    ok = N.notify_status_change(
        JOB, "offer", {"notifications": {"on_offer": True, "email_to": "me@x.com"}})
    assert ok is True and sent[0][0] == "me@x.com" and "OFFER" in sent[0][1]


def test_toggle_off_no_send(monkeypatch):
    sent = _capture(monkeypatch)
    assert N.notify_status_change(
        JOB, "interview", {"notifications": {"on_interview": False}}) is False
    assert sent == []


def test_non_milestone_no_send(monkeypatch):
    sent = _capture(monkeypatch)
    assert N.notify_status_change(JOB, "applied", {"notifications": {"on_offer": True}}) is False
    assert sent == []


def test_default_recipient_used(monkeypatch):
    sent = _capture(monkeypatch)
    ok = N.notify_status_change(
        JOB, "oa", {"notifications": {"on_oa": True}}, default_to="fallback@x.com")
    assert ok is True and sent[0][0] == "fallback@x.com"


def test_no_recipient_no_send(monkeypatch):
    sent = _capture(monkeypatch)
    assert N.notify_status_change(JOB, "offer", {"notifications": {"on_offer": True}}) is False
    assert sent == []
