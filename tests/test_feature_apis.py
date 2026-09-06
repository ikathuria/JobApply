"""
Endpoint tests for the new feature APIs: funnel analytics (M25), ATS match
(M21), and application follow-ups (M22). Handlers are called directly against a
throwaway SQLite DB injected via the module's cached connection.
"""

from datetime import date, timedelta

import pytest
from fastapi import HTTPException

import api.main as M
from tracker import tracker as T


@pytest.fixture
def conn(tmp_path, monkeypatch):
    c = T.init_db(tmp_path / "feat.db")
    monkeypatch.setattr(M, "_conn", c)
    yield c
    c.close()


def _add(conn, url, status, **kw):
    T.upsert_jobs(conn, [{"title": kw.get("title", "MLE"), "company": kw.get("company", "Acme"),
                          "url": url, "status": "new", "score": kw.get("score", 0.5),
                          "source": kw.get("source", "newgrad-jobs.com"),
                          "description": kw.get("description", "")}])
    jid = conn.execute("SELECT id FROM jobs WHERE url=?", (url,)).fetchone()["id"]
    upd = {k: kw[k] for k in ("date_applied",) if k in kw}
    if status != "new" or upd:
        T.update_status(conn, jid, status, **upd)
    return jid


# ── Funnel (M25) ────────────────────────────────────────────────────────────

def test_funnel_counts_and_rates(conn):
    _add(conn, "a1", "applied")
    _add(conn, "a2", "interview")
    _add(conn, "a3", "offer")
    _add(conn, "n1", "new")
    f = M.api_funnel()
    stages = {s["stage"]: s["count"] for s in f["funnel"]}
    # applied count rolls forward: applied+interview+offer all "reached" applied.
    assert stages["applied"] == 3
    assert stages["interview"] == 2   # interview + offer
    assert stages["offer"] == 1
    assert f["applied_total"] == 3
    assert f["response_rate"] == round(2 / 3, 3)      # oa+interview+offer = 2 of 3
    assert f["interview_rate"] == round(2 / 3, 3)     # interview+offer = 2 of 3
    assert "newgrad-jobs.com" in f["by_source"]


def test_funnel_empty(conn):
    f = M.api_funnel()
    assert f["applied_total"] == 0
    assert f["response_rate"] == 0.0


# ── ATS match (M21) ─────────────────────────────────────────────────────────

def test_ats_match_endpoint(conn):
    jid = _add(conn, "j1", "new", description="We need Python and Kubernetes.")
    m = M.api_ats_match(jid)
    assert "python" in m["jd_keywords"] and "kubernetes" in m["jd_keywords"]
    assert m["score"] is not None


def test_ats_match_no_description(conn):
    jid = _add(conn, "j2", "new", description="")
    m = M.api_ats_match(jid)
    assert m["score"] is None and "note" in m


def test_ats_match_404(conn):
    with pytest.raises(HTTPException):
        M.api_ats_match(999999)


# ── Application follow-ups (M22) ────────────────────────────────────────────

def test_followups_endpoint(conn):
    _add(conn, "old", "applied", date_applied=(date.today() - timedelta(days=10)).isoformat())
    _add(conn, "fresh", "applied", date_applied=(date.today() - timedelta(days=1)).isoformat())
    due = M.api_application_followups(days=7)
    urls = {d["url"] for d in due}
    assert "old" in urls and "fresh" not in urls


def test_followup_draft_endpoint(conn):
    jid = _add(conn, "j", "applied", title="ML Engineer", company="Stripe")
    d = M.api_application_followup_draft(jid)
    assert "ML Engineer" in d["body"] and "Stripe" in d["body"]
