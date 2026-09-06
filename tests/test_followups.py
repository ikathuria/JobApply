"""Tests for application follow-ups (M22)."""

from datetime import date, timedelta

import pytest

from pipeline import followups
from tracker import tracker as T


@pytest.fixture
def conn(tmp_path):
    c = T.init_db(tmp_path / "fu.db")
    yield c
    c.close()


def _add_applied(conn, url, days_ago):
    T.upsert_jobs(conn, [{"title": "MLE", "company": "Acme", "url": url, "status": "new"}])
    jid = conn.execute("SELECT id FROM jobs WHERE url=?", (url,)).fetchone()["id"]
    applied = (date.today() - timedelta(days=days_ago)).isoformat()
    T.update_status(conn, jid, "applied", date_applied=applied)
    return jid


def test_stale_applications_filters_by_age(conn):
    _add_applied(conn, "old", 10)
    _add_applied(conn, "fresh", 2)
    stale = followups.stale_applications(conn, days=7)
    urls = {j["url"] for j in stale}
    assert "old" in urls and "fresh" not in urls


def test_stale_reports_days_since(conn):
    _add_applied(conn, "old", 10)
    stale = followups.stale_applications(conn, days=7)
    assert stale[0]["days_since_applied"] == 10


def test_non_applied_excluded(conn):
    T.upsert_jobs(conn, [{"title": "MLE", "company": "Acme", "url": "iv", "status": "new"}])
    jid = conn.execute("SELECT id FROM jobs WHERE url='iv'").fetchone()["id"]
    T.update_status(conn, jid, "interview",
                    date_applied=(date.today() - timedelta(days=30)).isoformat())
    assert followups.stale_applications(conn, days=7) == []


def test_draft_followup_mentions_role_and_name():
    d = followups.draft_followup({"title": "ML Engineer", "company": "Stripe"},
                                 {"name": "Ishani Kathuria"})
    assert "ML Engineer" in d["body"] and "Stripe" in d["body"]
    assert "Ishani Kathuria" in d["body"]
    assert d["subject"]
