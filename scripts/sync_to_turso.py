#!/usr/bin/env python3
"""
Push local personal state up to Turso so the cloud daily reminder (GitHub
Actions) sees your real progress — not just the scraped jobs.

Turso holds GHA's freshly scraped 'new' jobs; everything you *do* (approve,
apply, interview, plus your LinkedIn connections and the DMs you've logged)
lives in the local SQLite DB. This mirrors that up:

  - jobs you've acted on (status != 'new')     → upsert into Turso by url
  - recruiters                                  → upsert (dedup by linkedin_url,
                                                  else email, else name+company)
  - outreach                                    → mirror (Turso's outreach is a
                                                  pure projection of local)

New jobs stay Turso's (the daily scrape owns them); this never deletes them.

Run locally — needs TURSO_DATABASE_URL + TURSO_AUTH_TOKEN in your .env:
    python scripts/sync_to_turso.py --dry-run   # preview counts, no writes
    python scripts/sync_to_turso.py             # perform the sync
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ModuleNotFoundError:
    pass

from tracker.tracker import DB_PATH, connect as sqlite_connect  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

# Job columns mirrored to Turso (everything meaningful except identity/timestamps).
_JOB_COLS = [
    "title", "company", "location", "url", "source_url", "source", "score",
    "status", "easy_apply", "description", "date_scraped", "date_applied",
    "resume_path", "cover_letter", "notes", "rejection_stage", "starred",
    "interview_date", "recruiter", "salary_range", "follow_up_date",
]


def _norm(s: str | None) -> str:
    return (s or "").strip().lower()


def sync_jobs(local, turso, dry_run: bool) -> int:
    rows = local.execute("SELECT * FROM jobs WHERE status != 'new'").fetchall()
    if dry_run or not rows:
        return len(rows)
    placeholders = ", ".join("?" * len(_JOB_COLS))
    updates = ", ".join(f"{c}=excluded.{c}" for c in _JOB_COLS if c != "url")
    sql = (
        f"INSERT INTO jobs ({', '.join(_JOB_COLS)}) VALUES ({placeholders}) "
        f"ON CONFLICT(url) DO UPDATE SET {updates}"
    )
    for r in rows:
        turso.execute(sql, [r[c] for c in _JOB_COLS])
    turso.commit()
    return len(rows)


def sync_recruiters(local, turso, dry_run: bool) -> tuple[dict[int, int], int, int]:
    """Upsert recruiters into Turso; return (local_id -> turso_id map, new, updated)."""
    local_recs = local.execute("SELECT * FROM recruiters").fetchall()
    turso_recs = turso.execute(
        "SELECT id, name, company, email, linkedin_url FROM recruiters"
    ).fetchall()

    by_url, by_email, by_nameco = {}, {}, {}
    for t in turso_recs:
        if _norm(t["linkedin_url"]):
            by_url[_norm(t["linkedin_url"])] = t["id"]
        if _norm(t["email"]):
            by_email[_norm(t["email"])] = t["id"]
        by_nameco[(_norm(t["name"]), _norm(t["company"]))] = t["id"]

    id_map: dict[int, int] = {}
    new = updated = 0
    for r in local_recs:
        tid = (by_url.get(_norm(r["linkedin_url"]))
               or by_email.get(_norm(r["email"]))
               or by_nameco.get((_norm(r["name"]), _norm(r["company"]))))
        if dry_run:
            if tid:
                updated += 1
            else:
                new += 1
            continue
        if tid:
            turso.execute(
                "UPDATE recruiters SET name=?, email=?, company=?, title=?, "
                "linkedin_url=?, source=?, notes=? WHERE id=?",
                [r["name"], r["email"], r["company"], r["title"],
                 r["linkedin_url"], r["source"], r["notes"], tid],
            )
            updated += 1
        else:
            turso.execute(
                "INSERT INTO recruiters (name, email, company, title, linkedin_url, source, notes) "
                "VALUES (?,?,?,?,?,?,?)",
                [r["name"], r["email"], r["company"], r["title"],
                 r["linkedin_url"], r["source"], r["notes"]],
            )
            tid = turso.execute("SELECT last_insert_rowid()").fetchone()[0]
            new += 1
        id_map[r["id"]] = tid
    turso.commit()
    return id_map, new, updated


def sync_outreach(local, turso, id_map: dict[int, int], dry_run: bool) -> int:
    """Mirror local outreach into Turso (recruiter_id remapped; job_id dropped —
    job ids differ across DBs and the reminder doesn't use it)."""
    rows = local.execute("SELECT * FROM outreach").fetchall()
    if dry_run:
        return len(rows)
    turso.execute("DELETE FROM outreach")
    n = 0
    for r in rows:
        rid = id_map.get(r["recruiter_id"])
        if rid is None:
            continue
        turso.execute(
            "INSERT INTO outreach (recruiter_id, job_id, type, subject, body, status, "
            "sent_at, reply_received_at, follow_up_date, notes) "
            "VALUES (?,?,?,?,?,?,?,?,?,?)",
            [rid, None, r["type"], r["subject"], r["body"], r["status"],
             r["sent_at"], r["reply_received_at"], r["follow_up_date"], r["notes"]],
        )
        n += 1
    turso.commit()
    return n


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true", help="Preview counts without writing")
    args = ap.parse_args()

    if not os.environ.get("TURSO_DATABASE_URL"):
        logger.error("error: TURSO_DATABASE_URL not set. Add TURSO_DATABASE_URL + "
                     "TURSO_AUTH_TOKEN to your .env (same values as the GitHub secrets).")
        return 1
    if not DB_PATH.exists():
        logger.error(f"error: local DB not found at {DB_PATH}")
        return 1

    from api.turso import connect as turso_connect
    from tracker.tracker import _create_tables

    local = sqlite_connect(DB_PATH)
    turso = turso_connect()
    _create_tables(turso)

    mode = "DRY RUN — no writes" if args.dry_run else "syncing"
    logger.info(f"Local → Turso ({mode})")

    n_jobs = sync_jobs(local, turso, args.dry_run)
    id_map, rec_new, rec_upd = sync_recruiters(local, turso, args.dry_run)
    n_out = sync_outreach(local, turso, id_map, args.dry_run)

    logger.info(f"  jobs (status != new):   {n_jobs} upserted")
    if args.dry_run:
        logger.info(f"  recruiters:             {rec_new} new + {rec_upd} existing")
    else:
        logger.info(f"  recruiters:             {rec_new} new, {rec_upd} updated")
    logger.info(f"  outreach:               {n_out} mirrored")
    logger.info("Done." if not args.dry_run else "Dry run complete — re-run without --dry-run to apply.")
    local.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
