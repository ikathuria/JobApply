"""Tests for the local→Turso sync (M36).

We can't reach a real Turso here, but the sync functions take generic DB-API
connections, so we exercise them with two local SQLite DBs (one standing in for
local, one for the 'remote'). This validates the upsert/mirror SQL + the
recruiter id-remapping without any network.
"""

import importlib.util
from datetime import date, timedelta
from pathlib import Path

import pytest

from tracker import tracker as T

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("sync_to_turso", ROOT / "scripts" / "sync_to_turso.py")
sync = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sync)


@pytest.fixture
def dbs(tmp_path):
    local = T.init_db(tmp_path / "local.db")
    remote = T.init_db(tmp_path / "remote.db")
    yield local, remote
    local.close()
    remote.close()


def test_sync_pushes_progress_and_preserves_remote_new_jobs(dbs):
    local, remote = dbs

    # Local: a new job (should NOT sync), an applied job, a queued job.
    T.upsert_jobs(local, [
        {"title": "New MLE", "company": "Acme", "url": "u-new", "status": "new"},
        {"title": "Applied RS", "company": "Amazon", "url": "u-app", "status": "new"},
        {"title": "Queued DS", "company": "Google", "url": "u-q", "status": "new"},
    ])
    aid = local.execute("SELECT id FROM jobs WHERE url='u-app'").fetchone()["id"]
    T.update_status(local, aid, "applied",
                    date_applied=(date.today() - timedelta(days=10)).isoformat())
    qid = local.execute("SELECT id FROM jobs WHERE url='u-q'").fetchone()["id"]
    T.update_status(local, qid, "queued")

    # Local recruiters + outreach (one messaged connection).
    rid = T.add_recruiter(local, "Ada Lovelace", company="Amazon",
                          linkedin_url="https://linkedin.com/in/ada", source="linkedin")
    T.add_outreach(local, rid, type=T.OUTREACH_LINKEDIN, status=T.OUTREACH_SENT)

    # Remote already has a freshly-scraped 'new' job — must be preserved.
    T.upsert_jobs(remote, [
        {"title": "Fresh scrape", "company": "Stripe", "url": "u-fresh", "status": "new"},
    ])

    id_map, rec_new, rec_upd = sync.sync_recruiters(local, remote, dry_run=False)
    n_jobs = sync.sync_jobs(local, remote, dry_run=False)
    n_out = sync.sync_outreach(local, remote, id_map, dry_run=False)

    assert n_jobs == 2                      # applied + queued, not the 'new' one
    assert rec_new == 1 and rec_upd == 0
    assert n_out == 1

    # Remote now has the applied + queued jobs, the recruiter, and the outreach.
    statuses = {r["url"]: r["status"] for r in remote.execute("SELECT url, status FROM jobs").fetchall()}
    assert statuses.get("u-app") == "applied"
    assert statuses.get("u-q") == "queued"
    assert "u-new" not in statuses          # local 'new' not pushed
    assert statuses.get("u-fresh") == "new"  # remote scrape preserved

    rrow = remote.execute("SELECT id, name FROM recruiters WHERE linkedin_url='https://linkedin.com/in/ada'").fetchone()
    assert rrow and rrow["name"] == "Ada Lovelace"
    orow = remote.execute("SELECT recruiter_id, status, type FROM outreach").fetchone()
    assert orow["recruiter_id"] == rrow["id"] and orow["status"] == "sent" and orow["type"] == "linkedin"


def test_sync_is_idempotent_and_updates_existing(dbs):
    local, remote = dbs
    T.upsert_jobs(local, [{"title": "RS", "company": "Amazon", "url": "u1", "status": "new"}])
    jid = local.execute("SELECT id FROM jobs WHERE url='u1'").fetchone()["id"]
    T.update_status(local, jid, "applied")
    rid = T.add_recruiter(local, "Grace Hopper", company="IBM", email="grace@ibm.com", source="linkedin")
    T.add_outreach(local, rid, type=T.OUTREACH_LINKEDIN, status=T.OUTREACH_SENT)

    for _ in range(2):  # run twice — must not duplicate
        id_map, _, _ = sync.sync_recruiters(local, remote, dry_run=False)
        sync.sync_jobs(local, remote, dry_run=False)
        sync.sync_outreach(local, remote, id_map, dry_run=False)

    assert remote.execute("SELECT COUNT(*) c FROM jobs").fetchone()["c"] == 1
    assert remote.execute("SELECT COUNT(*) c FROM recruiters").fetchone()["c"] == 1
    assert remote.execute("SELECT COUNT(*) c FROM outreach").fetchone()["c"] == 1
