"""
Sweep `new` Jobright jobs: skip the closed ones and swap the Jobright link for the
employer's own posting URL when one can be found.

Resumable: only jobs whose ``url`` is still a Jobright link are visited, so a run
cut short by rate limiting picks up where it stopped. Stops at the first
JobrightBlocked (the bot "Security check" page) instead of hammering the site.
"""

from __future__ import annotations

import logging
import time
from datetime import date

from tracker.tracker import STATUS_NEW, STATUS_SKIPPED, update_status

logger = logging.getLogger(__name__)


def refresh_new_jobs(conn, limit: int = 50, delay: float = 4.0, enrich=None) -> dict:
    """Returns counts: ``checked``, ``closed``, ``relinked``, ``blocked`` (bool)."""
    from pipeline.jobright_enricher import JobrightBlocked, enrich_jobright_url

    enrich = enrich or enrich_jobright_url
    rows = conn.execute(
        "SELECT * FROM jobs WHERE status = ? AND url LIKE '%jobright.ai/jobs/info/%' "
        "ORDER BY score DESC, created_at DESC LIMIT ?",
        (STATUS_NEW, limit),
    ).fetchall()

    counts = {"checked": 0, "closed": 0, "relinked": 0, "blocked": False}
    for i, row in enumerate(rows):
        job = dict(row) if hasattr(row, "keys") else row
        jobright_url = job["source_url"] or job["url"]
        if i and delay:
            time.sleep(delay)
        try:
            e = enrich(jobright_url)
        except JobrightBlocked:
            logger.warning("Jobright rate-limited after %d jobs; stopping", counts["checked"])
            counts["blocked"] = True
            break
        except Exception as exc:  # network hiccup on one job: move on
            logger.warning("Could not check job %s: %s", job["id"], exc)
            continue

        counts["checked"] += 1
        if e.is_closed:
            note = f"[closed {date.today().isoformat()}: {e.closed_reason}]"
            notes = f"{job.get('notes') or ''} {note}".strip()
            update_status(conn, job["id"], STATUS_SKIPPED, source_url=jobright_url, notes=notes)
            counts["closed"] += 1
        elif e.employer_url and "jobright.ai" not in e.employer_url:
            update_status(conn, job["id"], STATUS_NEW, source_url=jobright_url, url=e.employer_url)
            counts["relinked"] += 1
    return counts
