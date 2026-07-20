"""Tests for the /api/health probe (M11)."""

import pytest

import api.main as M
from tracker import tracker as T


@pytest.fixture
def conn(tmp_path, monkeypatch):
    c = T.init_db(tmp_path / "health.db")
    monkeypatch.setattr(M, "_conn", c)
    yield c
    c.close()


def test_health_ok_sqlite(conn, monkeypatch):
    monkeypatch.delenv("TURSO_DATABASE_URL", raising=False)
    h = M.api_health()
    assert h["status"] == "ok"
    assert h["db"] == "sqlite"
    assert h["jobs"] == 0


def test_health_reports_turso_backend(conn, monkeypatch):
    monkeypatch.setenv("TURSO_DATABASE_URL", "libsql://example")
    assert M.api_health()["db"] == "turso"


def test_health_counts_jobs(conn, monkeypatch):
    monkeypatch.delenv("TURSO_DATABASE_URL", raising=False)
    T.upsert_jobs(conn, [{"title": "X", "company": "Y", "url": "h1", "status": "new"}])
    assert M.api_health()["jobs"] == 1
