"""
Tracker-level tests for recruiting-timeline reminders (M19).

Uses a throwaway SQLite DB per test — no live server, no real tracker DB.
"""

import pytest

from tracker import tracker as T


@pytest.fixture
def conn(tmp_path):
    c = T.init_db(tmp_path / "reminders_test.db")
    yield c
    c.close()


def test_add_and_get_reminder(conn):
    rid = T.add_reminder(conn, "Google", kind=T.REMINDER_APPLY, due_date="2026-10-15",
                         note="Apply when it opens")
    r = T.get_reminder(conn, rid)
    assert r["company"] == "Google"
    assert r["kind"] == "apply"
    assert r["due_date"] == "2026-10-15"
    assert r["done"] == 0


def test_default_kind_and_blank_due(conn):
    rid = T.add_reminder(conn, "Amazon")            # defaults
    r = T.get_reminder(conn, rid)
    assert r["kind"] == T.REMINDER_APPLY
    assert r["due_date"] is None                     # blank normalized to NULL


def test_list_orders_open_before_done_then_by_due(conn):
    T.add_reminder(conn, "A", due_date="2026-09-01")
    T.add_reminder(conn, "B", due_date="2026-08-01")
    c = T.add_reminder(conn, "C", due_date="2026-07-01")
    T.update_reminder(conn, c, done=1)               # done sinks to the bottom
    order = [r["company"] for r in T.list_reminders(conn)]
    assert order == ["B", "A", "C"]                  # open (soonest first), then done
    assert [r["company"] for r in T.list_reminders(conn, include_done=False)] == ["B", "A"]


def test_reminders_due_excludes_future_and_done(conn):
    T.add_reminder(conn, "DueToday", due_date="2026-07-19")
    T.add_reminder(conn, "PastDue", due_date="2026-07-01")
    T.add_reminder(conn, "Future", due_date="2026-12-01")
    done_id = T.add_reminder(conn, "DoneButDue", due_date="2026-07-01")
    T.update_reminder(conn, done_id, done=1)

    due = T.list_reminders_due(conn, "2026-07-19")
    names = {r["company"] for r in due}
    assert names == {"DueToday", "PastDue"}          # future + done excluded


def test_update_toggle_done_and_delete(conn):
    rid = T.add_reminder(conn, "Meta", due_date="2026-09-01")
    T.update_reminder(conn, rid, done=1)
    assert T.get_reminder(conn, rid)["done"] == 1
    T.update_reminder(conn, rid, done=0, note="reopened")
    r = T.get_reminder(conn, rid)
    assert r["done"] == 0 and r["note"] == "reopened"

    T.delete_reminder(conn, rid)
    assert T.get_reminder(conn, rid) is None
