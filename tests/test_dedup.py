"""Tests for cross-source duplicate detection (M24)."""

import pytest

from pipeline import dedup
from tracker import tracker as T


def test_find_duplicate_groups_normalizes_title_and_company():
    jobs = [
        {"id": 1, "company": "Stripe", "title": "ML Engineer Intern - Summer 2026", "score": 0.5},
        {"id": 2, "company": "Stripe, Inc.", "title": "ML Engineer (New Grad)", "score": 0.9},
        {"id": 3, "company": "Databricks", "title": "Data Scientist", "score": 0.7},
    ]
    groups = dedup.find_duplicate_groups(jobs)
    assert len(groups) == 1
    grp = groups[0]
    assert [j["id"] for j in grp] == [2, 1]  # best score first


def test_no_false_group_on_empty_fields():
    jobs = [
        {"id": 1, "company": "", "title": "", "score": 0.1},
        {"id": 2, "company": "", "title": "", "score": 0.2},
    ]
    assert dedup.find_duplicate_groups(jobs) == []


@pytest.fixture
def conn(tmp_path):
    c = T.init_db(tmp_path / "dedup.db")
    yield c
    c.close()


def test_dedup_new_jobs_skips_extras_keeps_best(conn):
    T.upsert_jobs(conn, [
        {"title": "ML Engineer Intern Summer 2026", "company": "Stripe", "url": "a", "score": 0.5},
        {"title": "ML Engineer New Grad", "company": "Stripe Inc", "url": "b", "score": 0.9},
        {"title": "Data Scientist", "company": "Databricks", "url": "c", "score": 0.7},
    ])
    groups = dedup.dedup_new_jobs(conn)
    assert len(groups) == 1
    statuses = {r["url"]: r["status"] for r in conn.execute("SELECT url, status FROM jobs")}
    assert statuses["b"] == "new"        # keeper (higher score)
    assert statuses["a"] == "skipped"    # duplicate
    assert statuses["c"] == "new"        # unrelated
    note = conn.execute("SELECT notes FROM jobs WHERE url='a'").fetchone()["notes"]
    assert "duplicate of" in note


def test_dedup_ignores_non_new_jobs(conn):
    T.upsert_jobs(conn, [
        {"title": "ML Engineer", "company": "Stripe", "url": "a", "score": 0.5},
        {"title": "ML Engineer", "company": "Stripe", "url": "b", "score": 0.9},
    ])
    jid_a = conn.execute("SELECT id FROM jobs WHERE url='a'").fetchone()["id"]
    T.update_status(conn, jid_a, "applied")  # not 'new' → excluded from dedup
    groups = dedup.dedup_new_jobs(conn)
    assert groups == []  # only one 'new' job left, no group
    assert conn.execute("SELECT status FROM jobs WHERE url='a'").fetchone()["status"] == "applied"
