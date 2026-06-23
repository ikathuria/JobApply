"""
Unit tests for recruiter + outreach CRUD in tracker.tracker.

Uses a throwaway on-disk SQLite DB (via tmp_path) so schema creation, the
UNIQUE-email constraint, and the manual cascade-delete all exercise real SQL.
"""

import sqlite3

import pytest

from tracker import tracker as T


@pytest.fixture
def conn(tmp_path):
    c = T.init_db(tmp_path / "test.db")
    yield c
    c.close()


def test_tables_exist(conn):
    names = {
        r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    assert {"jobs", "recruiters", "outreach"} <= names


def test_add_and_get_recruiter(conn):
    rid = T.add_recruiter(conn, "Jane Doe", email="jane@acme.com", company="Acme", title="Recruiter")
    assert isinstance(rid, int) and rid > 0
    r = T.get_recruiter(conn, rid)
    assert r["name"] == "Jane Doe"
    assert r["email"] == "jane@acme.com"
    assert r["company"] == "Acme"
    assert r["source"] == "manual"


def test_blank_email_stored_as_null(conn):
    rid = T.add_recruiter(conn, "No Email", email="   ")
    assert T.get_recruiter(conn, rid)["email"] is None
    # multiple NULL emails are allowed (no UNIQUE collision)
    rid2 = T.add_recruiter(conn, "Also None", email=None)
    assert T.get_recruiter(conn, rid2)["email"] is None


def test_duplicate_email_raises(conn):
    T.add_recruiter(conn, "A", email="dup@x.com")
    with pytest.raises(sqlite3.IntegrityError):
        T.add_recruiter(conn, "B", email="dup@x.com")


def test_get_recruiter_by_email(conn):
    T.add_recruiter(conn, "Find Me", email="find@x.com")
    assert T.get_recruiter_by_email(conn, "find@x.com")["name"] == "Find Me"
    assert T.get_recruiter_by_email(conn, "missing@x.com") is None


def test_update_recruiter(conn):
    rid = T.add_recruiter(conn, "Old Name")
    T.update_recruiter(conn, rid, name="New Name", title="Sr Recruiter", notes="warm lead")
    r = T.get_recruiter(conn, rid)
    assert r["name"] == "New Name"
    assert r["title"] == "Sr Recruiter"
    assert r["notes"] == "warm lead"


def test_list_recruiters_with_counts(conn):
    rid = T.add_recruiter(conn, "Counts", email="counts@x.com")
    T.add_outreach(conn, rid, subject="hi")
    oid = T.add_outreach(conn, rid, subject="hello")
    T.update_outreach_status(conn, oid, T.OUTREACH_SENT)
    rows = T.list_recruiters(conn)
    row = next(r for r in rows if r["id"] == rid)
    assert row["outreach_count"] == 2
    assert row["sent_count"] == 1


def test_add_outreach_and_list(conn):
    rid = T.add_recruiter(conn, "R", email="r@x.com")
    oid = T.add_outreach(conn, rid, type=T.OUTREACH_COLD, subject="Subj", body="Body", job_id=None)
    o = T.get_outreach(conn, oid)
    assert o["recruiter_id"] == rid
    assert o["type"] == "cold_email"
    assert o["status"] == "draft"
    listed = T.list_outreach_for_recruiter(conn, rid)
    assert len(listed) == 1 and listed[0]["id"] == oid


def test_update_outreach_status_sets_fields(conn):
    rid = T.add_recruiter(conn, "R", email="r2@x.com")
    oid = T.add_outreach(conn, rid, subject="s")
    T.update_outreach_status(
        conn, oid, T.OUTREACH_SENT,
        sent_at="2026-06-22T10:00:00", follow_up_date="2026-06-29",
    )
    o = T.get_outreach(conn, oid)
    assert o["status"] == "sent"
    assert o["sent_at"] == "2026-06-22T10:00:00"
    assert o["follow_up_date"] == "2026-06-29"


def test_list_followups_due(conn):
    rid = T.add_recruiter(conn, "R", email="fu@x.com")
    # due yesterday (sent), future (sent), and a draft due yesterday (excluded)
    due = T.add_outreach(conn, rid, subject="due")
    T.update_outreach_status(conn, due, T.OUTREACH_SENT, follow_up_date="2026-06-22")
    future = T.add_outreach(conn, rid, subject="future")
    T.update_outreach_status(conn, future, T.OUTREACH_SENT, follow_up_date="2026-12-31")
    draft = T.add_outreach(conn, rid, subject="still draft")
    T.update_outreach(conn, draft, follow_up_date="2026-06-22")  # status stays draft

    rows = T.list_followups_due(conn, "2026-06-23")
    ids = [r["id"] for r in rows]
    assert due in ids
    assert future not in ids      # follow-up still in the future
    assert draft not in ids       # not sent
    assert rows[0]["recruiter_name"] == "R"


def test_delete_recruiter_cascades_outreach(conn):
    rid = T.add_recruiter(conn, "Doomed", email="d@x.com")
    T.add_outreach(conn, rid, subject="a")
    T.add_outreach(conn, rid, subject="b")
    T.delete_recruiter(conn, rid)
    assert T.get_recruiter(conn, rid) is None
    assert T.list_outreach_for_recruiter(conn, rid) == []
