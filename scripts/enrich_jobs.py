"""
Enriches Jobright-sourced jobs from their detail page: by default only
pre-application jobs that still carry the short scrape-time snippet (newest
first, capped by --limit); --all re-enriches every Jobright job.

Updates: title, company, location, salary_range, description, employer URL.
Marks closed jobs — and jobs whose full JD rules out F-1/OPT (clearance,
citizenship, no sponsorship) — as skipped if they haven't been applied to yet.

Usage:
    python scripts/enrich_jobs.py
    python scripts/enrich_jobs.py --delay 2.0   # seconds between requests (default 1.5)
    python scripts/enrich_jobs.py --limit 100   # at most 100 jobs this run (default 400)
    python scripts/enrich_jobs.py --all         # full refresh of every Jobright job
"""

import argparse
import logging
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))

from tracker.tracker import init_db, update_status, DB_PATH
from pipeline.jobright_enricher import enrich_jobright_url
from pipeline.job_filter import work_auth_blocker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

PRE_APPLICATION_STATUSES = {"new", "queued", "approved"}


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


UNENRICHED_MAX_CHARS = 800  # scrape-time snippets are ~300 chars; enriched JDs are longer


def main(delay: float, limit: int = 400, everything: bool = False) -> None:
    conn = open_db()

    where = "source_url LIKE '%jobright.ai/jobs/info/%'"
    if not everything:
        where += (f" AND status IN ('new', 'queued', 'approved')"
                  f" AND LENGTH(COALESCE(description, '')) < {UNENRICHED_MAX_CHARS}")
    rows = conn.execute(f"""
        SELECT id, title, company, status, url, source_url
        FROM jobs
        WHERE {where}
        ORDER BY id DESC
        LIMIT ?
    """, (limit,)).fetchall()

    total = len(rows)
    if total == 0:
        logger.info("No Jobright jobs found in DB.")
        return

    logger.info("Found %d Jobright jobs to re-enrich.", total)

    updated = skipped_closed = skipped_auth = errors = 0

    for i, row in enumerate(rows, 1):
        job_id = row["id"]
        source_url = row["source_url"]
        current_status = row["status"]
        label = f"[{i}/{total}] #{job_id} {row['company']} — {row['title'][:50]}"

        try:
            enriched = enrich_jobright_url(source_url, search_fallback=False)
        except Exception as exc:
            logger.warning("%s  ERROR: %s", label, exc)
            errors += 1
            time.sleep(delay)
            continue

        if enriched.is_closed and current_status in PRE_APPLICATION_STATUSES:
            new_status = "skipped"
            skipped_closed += 1
            logger.info("%s  -> CLOSED (%s), marked skipped", label, enriched.closed_reason)
        elif current_status in PRE_APPLICATION_STATUSES and (
            blocker := work_auth_blocker(enriched.description)
        ):
            # Scrape-time text is a short snippet; the full JD is the first
            # chance to see "clearance required" / "no sponsorship".
            new_status = "skipped"
            skipped_auth += 1
            logger.info("%s  -> WORK-AUTH (%r), marked skipped", label, blocker)
        else:
            new_status = current_status

        fields: dict = {}
        if enriched.title:
            fields["title"] = enriched.title
        if enriched.company:
            fields["company"] = enriched.company
        if enriched.location:
            fields["location"] = enriched.location
        if enriched.salary_range:
            fields["salary_range"] = enriched.salary_range
        if enriched.description:
            fields["description"] = enriched.description
        if enriched.employer_url:
            conflict = conn.execute(
                "SELECT id FROM jobs WHERE url = ? AND id != ?",
                (enriched.employer_url, job_id),
            ).fetchone()
            if not conflict:
                fields["url"] = enriched.employer_url

        update_status(conn, job_id, new_status, **fields)
        updated += 1

        status_note = f"  employer_url={'yes' if enriched.employer_url else 'no'}"
        logger.info("%s  -> OK%s", label, status_note)

        time.sleep(delay)

    logger.info(
        "Done. %d updated, %d closed→skipped, %d work-auth→skipped, %d errors (out of %d total).",
        updated, skipped_closed, skipped_auth, errors, total,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Enrich Jobright jobs from their detail pages.")
    parser.add_argument("--delay", type=float, default=1.5,
                        help="Seconds to wait between requests (default: 1.5)")
    parser.add_argument("--limit", type=int, default=400, help="Max jobs this run (default: 400)")
    parser.add_argument("--all", action="store_true", help="Re-enrich every Jobright job")
    args = parser.parse_args()
    main(args.delay, limit=args.limit, everything=args.all)
