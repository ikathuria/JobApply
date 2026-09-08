"""Tests for the inbox scanner orchestration (M20). IMAP is fully mocked."""

import pytest

from pipeline import inbox_reader, inbox_scan
from tracker import tracker as T


@pytest.fixture
def conn(tmp_path):
    c = T.init_db(tmp_path / "scan.db")
    yield c
    c.close()


def _add(conn, title, company, url, status, **kw):
    T.upsert_jobs(conn, [{"title": title, "company": company, "url": url, "status": status}])
    jid = conn.execute("SELECT id FROM jobs WHERE url=?", (url,)).fetchone()["id"]
    if status != "new" or kw:
        T.update_status(conn, jid, status, **kw)
    return jid


def test_scan_advances_matching_job(conn, monkeypatch):
    jid = _add(conn, "MLE", "Stripe", "u1", "applied")
    monkeypatch.setattr(inbox_reader, "fetch_recent", lambda **k: [{
        "from": "recruiter@stripe.com",
        "subject": "Interview invitation",
        "body": "We'd like to schedule a phone screen. What's your availability?",
        "date": "",
    }])
    summary = inbox_scan.scan_inbox(conn, notify=False)
    assert summary["scanned"] == 1
    assert len(summary["updated"]) == 1
    u = summary["updated"][0]
    assert u["job_id"] == jid and u["old"] == "applied" and u["new"] == "interview"
    assert conn.execute("SELECT status FROM jobs WHERE id=?", (jid,)).fetchone()["status"] == "interview"


def test_scan_ignores_unmatched_company(conn, monkeypatch):
    _add(conn, "MLE", "Stripe", "u1", "applied")
    monkeypatch.setattr(inbox_reader, "fetch_recent", lambda **k: [{
        "from": "r@databricks.com", "subject": "Interview", "body": "schedule a call", "date": "",
    }])
    summary = inbox_scan.scan_inbox(conn, notify=False)
    assert summary["updated"] == []
    assert len(summary["unmatched"]) == 1


def test_scan_rejection_from_active(conn, monkeypatch):
    jid = _add(conn, "MLE", "Stripe", "u1", "applied")
    monkeypatch.setattr(inbox_reader, "fetch_recent", lambda **k: [{
        "from": "r@stripe.com", "subject": "Update",
        "body": "Unfortunately, we will not be moving forward with your application.", "date": "",
    }])
    inbox_scan.scan_inbox(conn, notify=False)
    assert conn.execute("SELECT status FROM jobs WHERE id=?", (jid,)).fetchone()["status"] == "rejected"


def test_scan_noise_leaves_status(conn, monkeypatch):
    jid = _add(conn, "MLE", "Stripe", "u1", "applied")
    monkeypatch.setattr(inbox_reader, "fetch_recent", lambda **k: [{
        "from": "r@stripe.com", "subject": "Thanks for applying",
        "body": "We received your application.", "date": "",
    }])
    summary = inbox_scan.scan_inbox(conn, notify=False)
    assert summary["updated"] == []
    assert conn.execute("SELECT status FROM jobs WHERE id=?", (jid,)).fetchone()["status"] == "applied"


def test_scan_no_regression_for_interview_then_oa(conn, monkeypatch):
    jid = _add(conn, "MLE", "Stripe", "u1", "interview")
    monkeypatch.setattr(inbox_reader, "fetch_recent", lambda **k: [{
        "from": "r@stripe.com", "subject": "Assessment",
        "body": "Please complete the online assessment.", "date": "",
    }])
    summary = inbox_scan.scan_inbox(conn, notify=False)
    # interview → oa would be a regression; job stays at interview.
    assert summary["updated"] == []
    assert conn.execute("SELECT status FROM jobs WHERE id=?", (jid,)).fetchone()["status"] == "interview"


# ── ingest mode (reconstruct funnel from email) ──────────────────────────────

def _msgs(monkeypatch, msgs):
    monkeypatch.setattr(inbox_reader, "fetch_recent", lambda **k: msgs)


def test_ingest_creates_application(conn, monkeypatch):
    _msgs(monkeypatch, [{
        "from": "jobs-noreply@linkedin.com",
        "subject": "Your application to ML Engineer at Databricks",
        "body": "Thanks for applying.", "date": "2026-09-01",
    }])
    summary = inbox_scan.scan_inbox(conn, notify=False, ingest=True, folders=["X"])
    assert len(summary["created"]) == 1
    row = conn.execute("SELECT * FROM jobs WHERE company='Databricks'").fetchone()
    assert row["status"] == "applied" and row["source"] == "email"
    assert row["date_applied"] == "2026-09-01"


def test_ingest_then_reject_same_company(conn, monkeypatch):
    _msgs(monkeypatch, [
        {"from": "x@linkedin.com", "subject": "Your application to MLE at Akuna Capital",
         "body": "applying", "date": "2026-09-01"},
        {"from": "no-reply@akunacapital.com", "subject": "Update from Akuna Capital",
         "body": "Unfortunately, we will not be moving forward.", "date": "2026-09-05"},
    ])
    summary = inbox_scan.scan_inbox(conn, notify=False, ingest=True, folders=["X"])
    # One application created, then advanced to rejected — not two rows.
    rows = conn.execute("SELECT status FROM jobs WHERE company='Akuna Capital'").fetchall()
    assert len(rows) == 1 and rows[0]["status"] == "rejected"
    assert len(summary["created"]) == 1 and len(summary["updated"]) == 1


def test_ingest_is_idempotent(conn, monkeypatch):
    msgs = [{"from": "x@linkedin.com", "subject": "Your application to MLE at Neuralink",
             "body": "applying", "date": "2026-09-01"}]
    _msgs(monkeypatch, msgs)
    inbox_scan.scan_inbox(conn, notify=False, ingest=True, folders=["X"])
    inbox_scan.scan_inbox(conn, notify=False, ingest=True, folders=["X"])
    rows = conn.execute("SELECT id FROM jobs WHERE company='Neuralink'").fetchall()
    assert len(rows) == 1  # no duplicate on re-run


def test_ingest_attaches_email_content(conn, monkeypatch):
    _msgs(monkeypatch, [{
        "from": "jobs-noreply@linkedin.com",
        "subject": "Your application to ML Engineer at Ramp",
        "body": "Thanks for applying! We received your resume for the ML Engineer role.",
        "date": "2026-09-01",
    }])
    inbox_scan.scan_inbox(conn, notify=False, ingest=True, folders=["X"])
    desc = conn.execute("SELECT description FROM jobs WHERE company='Ramp'").fetchone()["description"]
    assert "Your application to ML Engineer at Ramp" in desc
    assert "received your resume" in desc


def test_non_ingest_does_not_create(conn, monkeypatch):
    _msgs(monkeypatch, [{
        "from": "no-reply@akunacapital.com", "subject": "Next Steps with Akuna Capital: HackerRank",
        "body": "complete the online assessment", "date": "",
    }])
    summary = inbox_scan.scan_inbox(conn, notify=False, ingest=False, folders=["X"])
    assert summary.get("created") == []
    assert conn.execute("SELECT COUNT(*) c FROM jobs").fetchone()["c"] == 0
