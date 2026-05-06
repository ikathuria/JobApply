"""
Re-enriches all Jobright-sourced jobs in the DB using the Jobright detail page.

Updates: title, company, location, salary_range, description, employer URL.
Marks closed jobs as skipped if they haven't been applied to yet.

Usage:
    python scripts/enrich_jobs.py
    python scripts/enrich_jobs.py --delay 2.0   # seconds between requests (default 1.5)
"""

import argparse
import logging
import sys
import time
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from tracker.tracker import init_db, update_status, DB_PATH
from pipeline.jobright_enricher import enrich_jobright_url

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

PRE_APPLICATION_STATUSES = {"new", "queued", "approved"}


def main(delay: float) -> None:
    conn = init_db(DB_PATH)

    rows = conn.execute("""
        SELECT id, title, company, status, url, source_url
        FROM jobs
        WHERE source_url LIKE '%jobright.ai/jobs/info/%'
        ORDER BY id
    """).fetchall()

    total = len(rows)
    if total == 0:
        logger.info("No Jobright jobs found in DB.")
        return

    logger.info("Found %d Jobright jobs to re-enrich.", total)

    updated = skipped_closed = errors = 0

    for i, row in enumerate(rows, 1):
        job_id = row["id"]
        source_url = row["source_url"]
        current_status = row["status"]
        label = f"[{i}/{total}] #{job_id} {row['company']} — {row['title'][:50]}"

        try:
            enriched = enrich_jobright_url(source_url)
        except Exception as exc:
            logger.warning("%s  ERROR: %s", label, exc)
            errors += 1
            time.sleep(delay)
            continue

        if enriched.is_closed and current_status in PRE_APPLICATION_STATUSES:
            new_status = "skipped"
            skipped_closed += 1
            logger.info("%s  -> CLOSED (%s), marked skipped", label, enriched.closed_reason)
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
        "Done. %d updated, %d closed→skipped, %d errors (out of %d total).",
        updated, skipped_closed, errors, total,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Re-enrich all Jobright jobs in the DB.")
    parser.add_argument("--delay", type=float, default=1.5,
                        help="Seconds to wait between requests (default: 1.5)")
    args = parser.parse_args()
    main(args.delay)
