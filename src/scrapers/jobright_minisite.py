"""
Scraper for jobright.ai embedded "minisite" job tables.

intern-list.com and newgrad-jobs.com both embed the same virtualized table
component from jobright.ai. That component is backed by a public JSON endpoint:

    POST https://jobright.ai/swan/mini-sites/list?position=<offset>&count=<n>
    body: {"category": "<type>:<country>:<vertical>"}   e.g. "newgrad:us:ml_ai"
    ->   {"result": {"jobList": [...], "total": <int>}}

We page through that endpoint with plain ``requests`` — no browser. The endpoint
serves data anonymously (``swan/auth/newinfo`` reports ``logined: false``), so no
auth token is needed. ``total`` lets us paginate exactly rather than guess.

Both site scrapers (intern_list_scraper, newgrad_jobs_scraper) call
``scrape_minisite`` with their own category slug and source label.
"""

import logging
import time
from datetime import datetime, timezone

import requests

logger = logging.getLogger(__name__)

API_URL  = "https://jobright.ai/swan/mini-sites/list"
JOB_URL  = "https://jobright.ai/jobs/info/{job_id}"
PAGE_SIZE = 50

_HEADERS = {
    "content-type": "application/json",
    "origin": "https://jobright.ai",
    "user-agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
}


def _normalize(job: dict, source: str) -> dict | None:
    """Map a jobright API job object onto the pipeline's job dict schema."""
    job_id = job.get("jobId")
    props  = job.get("properties") or {}
    title  = (props.get("title") or "").strip()
    if not job_id or not title:
        return None

    return {
        "title":        title,
        "company":      (props.get("company") or "").strip(),
        "location":     (props.get("location") or "").strip(),
        "url":          JOB_URL.format(job_id=job_id),
        "source":       source,
        "work_mode":    (props.get("workModel") or "").strip(),
        "salary":       (props.get("salary") or "").strip(),
        "season":       (props.get("roleType") or props.get("expLevel") or "").strip(),
        "description":  (props.get("qualifications") or "").strip(),
        "date_scraped": datetime.now(timezone.utc).isoformat(),
    }


def scrape_minisite(category: str, source: str, max_rows: int = 500) -> list[dict]:
    """Scrape a jobright.ai minisite category via its JSON API.

    Args:
        category: the minisite slug, ``"<type>:<country>:<vertical>"``
            (e.g. ``"newgrad:us:ml_ai"``).
        source: label stored on each job dict (e.g. ``"newgrad-jobs.com"``).
        max_rows: hard cap on rows to collect.

    Returns a list of job dicts, deduplicated by URL.
    """
    referer = f"https://jobright.ai/minisites-jobs/{category.replace(':', '/')}?embed=true"
    headers = {**_HEADERS, "referer": referer}

    jobs_by_url: dict[str, dict] = {}
    position = 0
    total = max_rows

    while len(jobs_by_url) < max_rows and position < total:
        try:
            resp = requests.post(
                API_URL,
                params={"position": position, "count": PAGE_SIZE},
                json={"category": category},
                headers=headers,
                timeout=30,
            )
            resp.raise_for_status()
            result = (resp.json() or {}).get("result") or {}
        except (requests.RequestException, ValueError) as e:
            logger.error(f"{source}: API request failed at position {position}: {e}")
            break

        page = result.get("jobList") or []
        if result.get("total") is not None:
            total = min(int(result["total"]), max_rows)

        if not page:
            logger.info(f"{source}: empty page at position {position} — stopping.")
            break

        for raw in page:
            job = _normalize(raw, source)
            if job:
                jobs_by_url[job["url"]] = job

        logger.info(f"{source}: {len(jobs_by_url)}/{total} jobs collected (position {position})")
        position += PAGE_SIZE
        time.sleep(0.4)  # be polite to the endpoint

    jobs = list(jobs_by_url.values())[:max_rows]
    logger.info(f"{source}: {len(jobs)} jobs collected total.")
    return jobs
