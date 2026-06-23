"""
Marks 'new' jobs that require a PhD (with no sign a Master's is accepted) as
'skipped', so they drop out of the active pipeline view. Reversible — reopen
from the dashboard or by setting status back to 'new'.

Detection logic lives in pipeline.job_filter.is_phd_only (keeps "MS or PhD").

Usage:
    python scripts/skip_phd_jobs.py --dry-run   # preview only
    python scripts/skip_phd_jobs.py             # apply (marks skipped)
    python scripts/skip_phd_jobs.py --delete    # delete instead of skip
"""

import argparse
import logging
import os
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ModuleNotFoundError:
    pass

from tracker.tracker import init_db, DB_PATH
from pipeline.job_filter import is_phd_only

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def open_db():
    if os.environ.get("TURSO_DATABASE_URL"):
        from api.turso import connect as turso_connect, seed_from_sqlite
        from tracker.tracker import _create_tables
        conn = turso_connect()
        _create_tables(conn)
        seed_from_sqlite(conn, DB_PATH)
        return conn
    return init_db(DB_PATH)


def _text(row) -> str:
    parts = [row["title"] or "", row["company"] or "", row["description"] or ""]
    return " ".join(parts).lower()


def main(dry_run: bool, delete: bool) -> None:
    conn = open_db()
    rows = conn.execute(
        "SELECT id, title, company, description FROM jobs WHERE status = 'new'"
    ).fetchall()

    phd = [r for r in rows if is_phd_only(_text(r))]
    if not phd:
        logger.info("No PhD-only 'new' jobs found (of %d new jobs).", len(rows))
        return

    action = "delete" if delete else "skip"
    logger.info("Found %d PhD-only job(s) of %d new jobs — would %s:", len(phd), len(rows), action)
    for r in phd:
        logger.info("  id=%-6s  %-55s  %s", r["id"], (r["title"] or "")[:55], r["company"])

    if dry_run:
        logger.info("Dry-run mode — nothing changed.")
        return

    ids = [r["id"] for r in phd]
    if delete:
        conn.executemany("DELETE FROM jobs WHERE id = ?", [(i,) for i in ids])
        logger.info("Deleted %d PhD-only job(s).", len(ids))
    else:
        conn.executemany("UPDATE jobs SET status = 'skipped' WHERE id = ?", [(i,) for i in ids])
        logger.info("Marked %d PhD-only job(s) as skipped.", len(ids))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Skip (or delete) PhD-only jobs.")
    parser.add_argument("--dry-run", action="store_true", help="Preview without changing anything")
    parser.add_argument("--delete", action="store_true", help="Delete instead of marking skipped")
    args = parser.parse_args()
    main(dry_run=args.dry_run, delete=args.delete)
