"""
Endpoint tests for the recruiter + outreach API.

Calls the FastAPI handler functions directly against a throwaway SQLite DB
(injected by monkeypatching the module's cached connection), so no live server,
no httpx, and no pollution of the real tracker DB.
"""

import pytest
from fastapi import HTTPException

import api.main as M
from tracker import tracker as T


@pytest.fixture
def conn(tmp_path, monkeypatch):
    c = T.init_db(tmp_path / "api_test.db")
    monkeypatch.setattr(M, "_conn", c)  # db() returns this instead of the real DB
    yield c
    c.close()


def test_recruiters_empty_on_fresh_db(conn):
    assert M.api_list_recruiters() == []


def test_add_get_list_recruiter(conn):
    created = M.api_add_recruiter(M.RecruiterIn(name="Jane", email="jane@acme.com", company="Acme"))
    assert created["id"] > 0 and created["email"] == "jane@acme.com"

    fetched = M.api_get_recruiter(created["id"])
    assert fetched["name"] == "Jane"

    listed = M.api_list_recruiters()
    assert len(listed) == 1 and listed[0]["outreach_count"] == 0


def test_duplicate_email_returns_409(conn):
    M.api_add_recruiter(M.RecruiterIn(name="A", email="dup@x.com"))
    with pytest.raises(HTTPException) as exc:
        M.api_add_recruiter(M.RecruiterIn(name="B", email="dup@x.com"))
    assert exc.value.status_code == 409


def test_get_missing_recruiter_404(conn):
    with pytest.raises(HTTPException) as exc:
        M.api_get_recruiter(999)
    assert exc.value.status_code == 404


def test_patch_and_delete_recruiter(conn):
    rid = M.api_add_recruiter(M.RecruiterIn(name="Old"))["id"]
    patched = M.api_patch_recruiter(rid, M.RecruiterPatch(title="Sr Recruiter"))
    assert patched["title"] == "Sr Recruiter"

    deleted = M.api_delete_recruiter(rid)
    assert deleted["status"] == "deleted"
    with pytest.raises(HTTPException):
        M.api_get_recruiter(rid)


def test_outreach_flow(conn):
    rid = M.api_add_recruiter(M.RecruiterIn(name="R", email="r@x.com"))["id"]
    o = M.api_add_outreach(M.OutreachIn(recruiter_id=rid, subject="Hi", body="Hello", type="cold_email"))
    assert o["status"] == "draft" and o["recruiter_id"] == rid

    updated = M.api_patch_outreach(o["id"], M.OutreachPatch(status="sent", sent_at="2026-06-22T10:00:00"))
    assert updated["status"] == "sent"

    rows = M.api_recruiter_outreach(rid)
    assert len(rows) == 1 and rows[0]["id"] == o["id"]


def test_outreach_for_missing_recruiter_404(conn):
    with pytest.raises(HTTPException) as exc:
        M.api_add_outreach(M.OutreachIn(recruiter_id=12345, subject="x"))
    assert exc.value.status_code == 404
