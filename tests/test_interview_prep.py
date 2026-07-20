"""
Tests for the Interview Prep section (M9) — generator, prep table, endpoints.
The LLM call is mocked so no API key or network is needed.
"""

import json

import pytest
from fastapi import HTTPException

import api.main as M
from tracker import tracker as T
from pipeline import interview_prep as IP

CANNED = json.dumps({
    "snapshot": "Acme builds ML infra; strong fit for your RAG background.",
    "topics_to_review": ["RAG evaluation", "transformers"],
    "questions": {
        "behavioral": [{"q": "Tell me about a hard bug", "talking_points": ["AWS log summarization"]}],
        "technical": [{"q": "Explain attention", "talking_points": ["transformer internals"]}],
        "system_design": [{"q": "Design a RAG system", "talking_points": ["hybrid retrieval"]}],
    },
    "questions_to_ask": ["What does success look like in 6 months?"],
    "checklist": ["Sleep well", "Review your projects"],
})

_JOB = {
    "title": "Machine Learning Engineer, New Grad", "company": "Acme",
    "location": "USA",
    "description": "We build retrieval systems. " * 20,   # >200 chars so no JD fetch
}


@pytest.fixture
def conn(tmp_path, monkeypatch):
    c = T.init_db(tmp_path / "prep.db")
    monkeypatch.setattr(M, "_conn", c)
    yield c
    c.close()


# ── generator ─────────────────────────────────────────────────────────────────

def test_generate_prep_structure(monkeypatch):
    monkeypatch.setattr(IP, "complete", lambda *a, **k: CANNED)
    pack = IP.generate_prep(_JOB, "job description text")
    assert pack["snapshot"]
    assert "RAG evaluation" in pack["topics_to_review"]
    for bucket in ("behavioral", "technical", "system_design"):
        assert pack["questions"][bucket] and "q" in pack["questions"][bucket][0]
    assert pack["questions_to_ask"] and pack["checklist"]


def test_generate_prep_fills_defaults_on_sparse_json(monkeypatch):
    monkeypatch.setattr(IP, "complete", lambda *a, **k: "{}")
    pack = IP.generate_prep(_JOB, "jd")
    assert pack["questions"] == {"behavioral": [], "technical": [], "system_design": []}
    assert pack["topics_to_review"] == [] and pack["checklist"] == []


def test_generate_prep_invalid_json_returns_none(monkeypatch):
    monkeypatch.setattr(IP, "complete", lambda *a, **k: "sorry, not json")
    assert IP.generate_prep(_JOB, "jd") is None


# ── prep table CRUD ───────────────────────────────────────────────────────────

def test_prep_table_crud(conn):
    T.upsert_jobs(conn, [{**_JOB, "url": "p1", "status": "interview"}])
    jid = conn.execute("SELECT id FROM jobs WHERE url='p1'").fetchone()["id"]

    T.upsert_prep(conn, jid, CANNED, model="groq:test")
    row = T.get_prep(conn, jid)
    assert row and json.loads(row["content"])["snapshot"]

    T.upsert_prep(conn, jid, json.dumps({"snapshot": "v2"}), model="groq:test")  # replace
    assert json.loads(T.get_prep(conn, jid)["content"])["snapshot"] == "v2"

    T.delete_prep(conn, jid)
    assert T.get_prep(conn, jid) is None


def test_list_prep_jobs_only_interview_stage(conn):
    T.upsert_jobs(conn, [
        {**_JOB, "url": "a", "status": "interview"},
        {**_JOB, "url": "b", "status": "oa"},
        {**_JOB, "url": "c", "status": "new"},
        {**_JOB, "url": "d", "status": "applied"},
    ])
    listed = T.list_prep_jobs(conn)
    statuses = {r["status"] for r in listed}
    assert statuses == {"interview", "oa"}          # new/applied excluded
    assert all(r["has_prep"] == 0 for r in listed)  # none generated yet


# ── endpoints ─────────────────────────────────────────────────────────────────

def test_api_generate_get_delete_prep(conn, monkeypatch):
    monkeypatch.setattr(IP, "complete", lambda *a, **k: CANNED)
    T.upsert_jobs(conn, [{**_JOB, "url": "e1", "status": "interview"}])
    jid = conn.execute("SELECT id FROM jobs WHERE url='e1'").fetchone()["id"]

    gen = M.api_generate_prep(jid)
    assert gen["content"]["snapshot"] and gen["job_id"] == jid

    got = M.api_get_prep(jid)
    assert got["content"]["topics_to_review"] == ["RAG evaluation", "transformers"]

    # it now shows up flagged in the prep list
    listed = M.api_list_prep_jobs()
    assert any(r["id"] == jid and r["has_prep"] for r in listed)

    assert M.api_delete_prep(jid)["status"] == "deleted"
    with pytest.raises(HTTPException) as exc:
        M.api_get_prep(jid)
    assert exc.value.status_code == 404


def test_api_generate_prep_missing_job_404(conn):
    with pytest.raises(HTTPException) as exc:
        M.api_generate_prep(9999)
    assert exc.value.status_code == 404
