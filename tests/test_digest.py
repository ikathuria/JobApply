"""Tests for the weekly digest builder (M23)."""

from datetime import date, timedelta

import pytest

from pipeline import digest
from tracker import tracker as T


@pytest.fixture
def conn(tmp_path):
    c = T.init_db(tmp_path / "digest.db")
    yield c
    c.close()


def test_build_digest_sections(conn):
    # 2 new (scored), 1 queued, 1 stale application.
    T.upsert_jobs(conn, [
        {"title": "MLE", "company": "Stripe", "url": "n1", "status": "new", "score": 0.9},
        {"title": "DS", "company": "Databricks", "url": "n2", "status": "new", "score": 0.4},
        {"title": "AI Eng", "company": "OpenAI", "url": "q1", "status": "new"},
        {"title": "RS", "company": "Meta", "url": "a1", "status": "new"},
    ])
    qid = conn.execute("SELECT id FROM jobs WHERE url='q1'").fetchone()["id"]
    T.update_status(conn, qid, "queued")
    aid = conn.execute("SELECT id FROM jobs WHERE url='a1'").fetchone()["id"]
    T.update_status(conn, aid, "applied",
                    date_applied=(date.today() - timedelta(days=14)).isoformat())

    d = digest.build_digest(conn, today=date.today())
    s = d["sections"]
    assert len(s["new"]) == 2
    assert len(s["queued"]) == 1
    assert len(s["stale"]) == 1
    assert d["subject"].startswith("[JobApply]")
    assert "Stripe" in d["body"]  # top new job listed


def test_build_digest_empty(conn):
    d = digest.build_digest(conn, today=date.today())
    assert d["sections"]["new"] == []
    assert "0 new" in d["subject"]
