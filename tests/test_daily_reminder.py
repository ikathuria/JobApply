"""Tests for the daily reminder builder (M35)."""

from datetime import date, timedelta

import pytest

from pipeline import daily_reminder as R
from tracker import tracker as T


@pytest.fixture
def conn(tmp_path):
    c = T.init_db(tmp_path / "remind.db")
    yield c
    c.close()


def test_build_reminder_sections(conn):
    # approved (ready to apply), queued (to review), a sponsor new job, a stale app.
    T.upsert_jobs(conn, [
        {"title": "MLE", "company": "Stripe", "url": "ap1", "status": "new", "score": 0.9},
        {"title": "AI Eng", "company": "OpenAI", "url": "q1", "status": "new", "score": 0.8},
        {"title": "RS", "company": "Amazon", "url": "s1", "status": "new", "score": 0.95},  # sponsor
        {"title": "DS", "company": "Nowhere LLC", "url": "a1", "status": "new"},
    ])
    apid = conn.execute("SELECT id FROM jobs WHERE url='ap1'").fetchone()["id"]
    T.update_status(conn, apid, "approved")
    qid = conn.execute("SELECT id FROM jobs WHERE url='q1'").fetchone()["id"]
    T.update_status(conn, qid, "queued")
    aid = conn.execute("SELECT id FROM jobs WHERE url='a1'").fetchone()["id"]
    T.update_status(conn, aid, "applied",
                    date_applied=(date.today() - timedelta(days=10)).isoformat())

    # An un-contacted LinkedIn connection + one already messaged.
    rid = T.add_recruiter(conn, "Uncontacted", company="Amazon", source="linkedin")
    rid2 = T.add_recruiter(conn, "AlreadyDM'd", company="Google", source="linkedin")
    oid = T.add_outreach(conn, rid2, type=T.OUTREACH_LINKEDIN, status=T.OUTREACH_SENT)
    assert oid > 0

    r = R.build_reminder(conn, today=date.today())
    s = r["sections"]
    assert len(s["approved"]) == 1
    assert len(s["queued"]) == 1
    assert any(j["company"] == "Amazon" for j in s["sponsor_new"])  # known sponsor surfaced
    assert len(s["stale"]) == 1
    # Only the un-contacted linkedin connection shows up.
    names = {c["name"] for c in s["connections"]}
    assert "Uncontacted" in names and "AlreadyDM'd" not in names
    assert r["subject"].startswith("[JobApply] Today:")
    assert "APPLY TODAY" in r["body"] and "ASK FOR REFERRALS" in r["body"]
    assert rid > 0


def test_build_reminder_empty(conn):
    r = R.build_reminder(conn, today=date.today())
    assert r["sections"]["approved"] == []
    assert r["sections"]["connections"] == []
    assert "APPLY TODAY" in r["body"]
