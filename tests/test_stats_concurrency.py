"""Regression tests for the shared-connection concurrency bug (M-fix 2026-09-17).

`GET /api/stats` intermittently 500'd with `IndexError: tuple index out of
range` from `get_stats`: FastAPI ran ~7 queries in parallel on one shared
sqlite3 connection, crossing cursor state so a sqlite3.Row was built against a
column description that didn't match the underlying tuple. The fix hands each
thread its own sqlite connection via `db()`; these tests lock that in.
"""

import threading
from concurrent.futures import ThreadPoolExecutor

import pytest

import api.main as M
from tracker import tracker as T


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    monkeypatch.delenv("TURSO_DATABASE_URL", raising=False)
    dbp = tmp_path / "concurrent.db"
    c = T.init_db(dbp)
    T.upsert_jobs(c, [
        {"title": f"Role {i}", "company": f"Co{i}", "url": f"u{i}",
         "status": ["new", "ready", "applied", "interview"][i % 4]}
        for i in range(40)
    ])
    c.close()
    # Reset api.main's connection state so db() rebuilds against the temp DB.
    monkeypatch.setattr(M, "DB_PATH", dbp)
    monkeypatch.setattr(M, "_conn", None)
    monkeypatch.setattr(M, "_schema_ready", False)
    monkeypatch.setattr(M, "_local", threading.local())
    yield dbp


def test_db_returns_one_connection_per_thread(temp_db):
    seen = {}

    def grab():
        seen[threading.get_ident()] = M.db()

    threads = [threading.Thread(target=grab) for _ in range(6)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    conns = list(seen.values())
    assert len(conns) == 6
    # Each thread got a distinct connection object (no sharing → no cross-talk).
    assert len({id(c) for c in conns}) == 6


def test_same_thread_reuses_its_connection(temp_db):
    assert M.db() is M.db()


def test_concurrent_mixed_queries_do_not_crash(temp_db):
    """Hammer get_stats (2 cols) alongside a wide SELECT (~24 cols) from many
    threads. Under the old shared connection this raised intermittently."""
    errors = []

    def work(_):
        try:
            for _ in range(25):
                conn = M.db()
                stats = T.get_stats(conn)
                assert sum(stats.values()) == 40
                conn.execute("SELECT * FROM jobs").fetchall()
        except Exception as e:  # noqa: BLE001 — capture any thread failure
            errors.append(repr(e))

    with ThreadPoolExecutor(max_workers=8) as ex:
        list(ex.map(work, range(8)))

    assert not errors, errors
