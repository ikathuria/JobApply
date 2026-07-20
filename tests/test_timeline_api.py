"""
Endpoint tests for the recruiting-timeline + reminders API (M19).

Calls the FastAPI handler functions directly against a throwaway SQLite DB
(injected by monkeypatching the module's cached connection).
"""

from datetime import date

import pytest
from fastapi import HTTPException

import api.main as M
from tracker import tracker as T


@pytest.fixture
def conn(tmp_path, monkeypatch):
    c = T.init_db(tmp_path / "timeline_test.db")
    monkeypatch.setattr(M, "_conn", c)
    yield c
    c.close()


# ── window-status computation (date-deterministic) ────────────────────────────

def test_status_upcoming_before_open():
    comp = {"opens": "2026-08-15", "closes": "2026-10-31", "rolling": False}
    s = M._company_window_status(comp, date(2026, 7, 19))
    assert s["status"] == "upcoming"
    assert s["days_until_open"] == 27


def test_status_open_and_closing_soon():
    comp = {"opens": "2026-08-15", "closes": "2026-10-31", "rolling": False}
    assert M._company_window_status(comp, date(2026, 9, 1))["status"] == "open"
    near = M._company_window_status(comp, date(2026, 10, 20))
    assert near["status"] == "closing_soon"
    assert near["days_until_close"] == 11


def test_status_closed_after_close():
    comp = {"opens": "2026-08-15", "closes": "2026-10-31", "rolling": False}
    assert M._company_window_status(comp, date(2026, 12, 1))["status"] == "closed"


def test_status_rolling_stays_open_without_close():
    comp = {"opens": "2026-07-15", "closes": None, "rolling": True}
    assert M._company_window_status(comp, date(2026, 11, 1))["status"] == "rolling"
    # but rolling before its open date is still upcoming
    assert M._company_window_status(comp, date(2026, 7, 1))["status"] == "upcoming"


# ── /api/timeline ─────────────────────────────────────────────────────────────

def test_timeline_shape_and_counts(conn):
    # A live Amazon role + an Amazon recruiter should light up that company.
    T.upsert_jobs(conn, [{
        "title": "New Grad Applied Scientist", "company": "Amazon Web Services",
        "url": "https://x.test/1", "status": "new", "score": 0.9,
    }])
    T.add_recruiter(conn, "Ex Teammate", company="Amazon", email="ex@amazon.com")

    res = M.api_timeline()
    assert "companies" in res and len(res["companies"]) > 0
    by_name = {c["name"]: c for c in res["companies"]}
    assert "Amazon" in by_name
    amazon = by_name["Amazon"]
    assert amazon["open_roles"] >= 1        # alias "aws"/"amazon" matched the job
    assert amazon["has_contact"] is True
    assert "status" in amazon               # window status annotated


def test_timeline_ignores_non_applyable_jobs(conn):
    # rejected / skipped jobs must NOT count as open roles
    T.upsert_jobs(conn, [{
        "title": "ML Eng", "company": "Google", "url": "https://x.test/2",
        "status": "rejected", "score": 0.5,
    }])
    by_name = {c["name"]: c for c in M.api_timeline()["companies"]}
    assert by_name["Google"]["open_roles"] == 0


# ── reminders endpoints ───────────────────────────────────────────────────────

def test_reminder_crud_endpoints(conn):
    created = M.api_add_reminder(M.ReminderIn(
        company="Google", kind="apply", due_date="2026-10-15", note="tight window"))
    assert created["id"] > 0 and created["company"] == "Google"

    listed = M.api_list_reminders()
    assert len(listed) == 1

    patched = M.api_patch_reminder(created["id"], M.ReminderPatch(done=1))
    assert patched["done"] == 1

    deleted = M.api_delete_reminder(created["id"])
    assert deleted["status"] == "deleted"
    with pytest.raises(HTTPException) as exc:
        M.api_patch_reminder(created["id"], M.ReminderPatch(done=0))
    assert exc.value.status_code == 404


def test_reminder_requires_company(conn):
    with pytest.raises(HTTPException) as exc:
        M.api_add_reminder(M.ReminderIn(company="   "))
    assert exc.value.status_code == 400


def test_reminders_due_endpoint_filters(conn):
    from datetime import date as _date, timedelta
    past = (_date.today() - timedelta(days=1)).isoformat()
    future = (_date.today() + timedelta(days=30)).isoformat()
    M.api_add_reminder(M.ReminderIn(company="DuePast", due_date=past))
    M.api_add_reminder(M.ReminderIn(company="Future", due_date=future))

    due = M.api_reminders_due()
    names = {r["company"] for r in due}
    assert "DuePast" in names and "Future" not in names
