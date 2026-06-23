"""
Deletes jobs that are still in 'new' or 'queued' status and were created
more than 30 days ago — stale listings that were never acted on.

Usage:
    python scripts/cleanup_stale_jobs.py
    python scripts/cleanup_stale_jobs.py --dry-run   # preview only, no deletes
    python scripts/cleanup_stale_jobs.py --days 60   # custom age threshold
"""

import argparse
import logging
import os
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))

# Load .env so a local run targets the Turso cloud DB (when configured) rather
# than the local SQLite copy. No-op in CI where env vars come from the platform.
try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ModuleNotFoundError:
    pass

from tracker.tracker import init_db, DB_PATH

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

STALE_STATUSES = ("new", "queued")


def open_db():
    """Use Turso in CI/production when configured; otherwise use local SQLite."""
    if os.environ.get("TURSO_DATABASE_URL"):
        from api.turso import connect as turso_connect, seed_from_sqlite
        from tracker.tracker import _create_tables

        conn = turso_connect()
        _create_tables(conn)
        seed_from_sqlite(conn, DB_PATH)
        return conn

    return init_db(DB_PATH)


def main(days: int, dry_run: bool) -> None:
    conn = open_db()

    placeholders = ", ".join("?" * len(STALE_STATUSES))
    preview_sql = f"""
        SELECT id, title, company, status, created_at
        FROM jobs
        WHERE status IN ({placeholders})
          AND created_at <= datetime('now', '-{days} days')
        ORDER BY created_at
    """

    rows = conn.execute(preview_sql, list(STALE_STATUSES)).fetchall()

    if not rows:
        logger.info("No stale jobs found (older than %d days in %s).", days, STALE_STATUSES)
        return

    logger.info(
        "Found %d stale job(s) older than %d days with status in %s:",
        len(rows), days, STALE_STATUSES,
    )
    for r in rows:
        logger.info("  [%s] id=%-5s  %-50s  %s", r["status"], r["id"], r["title"][:50], r["company"])

    if dry_run:
        logger.info("Dry-run mode — no rows deleted.")
        return

    delete_sql = f"""
        DELETE FROM jobs
        WHERE status IN ({placeholders})
          AND created_at <= datetime('now', '-{days} days')
    """
    conn.execute(delete_sql, list(STALE_STATUSES))
    logger.info("Deleted %d stale job(s).", len(rows))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Delete stale unreviewed jobs.")
    parser.add_argument(
        "--days", type=int, default=30,
        help="Age threshold in days (default: 30)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Preview deletions without actually deleting",
    )
    args = parser.parse_args()
    main(days=args.days, dry_run=args.dry_run)
