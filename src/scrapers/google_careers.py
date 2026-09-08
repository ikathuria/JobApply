"""
Scraper for Google Careers (google.com/about/careers/applications).

The modern Google careers site is a wiz/JS app, but it *server-renders* each
search-results page into an ``AF_initDataCallback({key: 'ds:1', ... data: [...]})``
blob inside the initial HTML. We fetch that HTML with plain ``requests`` (no
browser) and parse the embedded JSON — the same browserless philosophy as
``scrapers.jobright_minisite``.

Results URL + query params::

    GET https://www.google.com/about/careers/applications/jobs/results/
        ?q=<free text>            e.g. "machine learning"
        &location=<place>         e.g. "United States", "India"
        &target_level=<level>     EARLY | INTERN_AND_APPRENTICE | MID | ADVANCED
        &page=<1-based index>

The ``ds:1`` blob is ``[jobList, _, total, _]`` where each job is a 21-field
list. The fields we consume are mapped in ``_FIELD`` below (verified 2026-09-08).

``scrape_google_careers`` fans out over queries x locations x target_levels,
pages each combination to exhaustion, and returns pipeline-schema job dicts
deduplicated by URL.
"""

import html as _html
import logging
import re
import time
from datetime import datetime, timezone

import requests

logger = logging.getLogger(__name__)

RESULTS_URL = "https://www.google.com/about/careers/applications/jobs/results/"
JOB_URL = "https://www.google.com/about/careers/applications/jobs/results/{job_id}"
PAGE_SIZE = 20  # Google returns 20 rows per page

# Human-readable label stored on each job's ``season`` field, per target_level.
_LEVEL_LABELS = {
    "EARLY": "Early Career",
    "INTERN_AND_APPRENTICE": "Intern",
    "MID": "Mid",
    "ADVANCED": "Advanced",
}

# Field indices within a single job list in the ds:1 blob.
_FIELD = {
    "id": 0,
    "title": 1,
    "responsibilities": 3,   # [null, "<html>"]
    "qualifications": 4,     # [null, "<html>"]
    "company": 7,
    "locations": 9,          # [[display, [addr], city, zip, state, country], ...]
}

_HEADERS = {
    "user-agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "accept-language": "en-US,en;q=0.9",
}

_DS1_RE = re.compile(
    r"AF_initDataCallback\(\{key: 'ds:1'.*?data:(\[.*?\]), sideChannel", re.S
)
_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(raw: str | None) -> str:
    """Flatten an HTML fragment to plain text (list items become '- ' lines)."""
    if not raw:
        return ""
    text = re.sub(r"<li[^>]*>", "\n- ", raw, flags=re.I)
    text = _TAG_RE.sub(" ", text)
    text = _html.unescape(text)
    return re.sub(r"[ \t]+", " ", text).strip()


def _cell_html(cell) -> str:
    """Fields like responsibilities/qualifications arrive as ``[null, "<html>"]``."""
    if isinstance(cell, list):
        return next((x for x in cell if isinstance(x, str)), "")
    return cell if isinstance(cell, str) else ""


def _locations(cell) -> str:
    if not isinstance(cell, list):
        return ""
    names = [loc[0] for loc in cell if isinstance(loc, list) and loc and loc[0]]
    return " | ".join(names[:5])


def _normalize(job: list, source: str, level_label: str) -> dict | None:
    """Map one ds:1 job list onto the pipeline's job dict schema."""
    if not isinstance(job, list) or len(job) <= _FIELD["locations"]:
        return None
    job_id = job[_FIELD["id"]]
    title = (job[_FIELD["title"]] or "").strip() if job[_FIELD["title"]] else ""
    if not job_id or not title:
        return None

    responsibilities = _strip_html(_cell_html(job[_FIELD["responsibilities"]]))
    qualifications = _strip_html(_cell_html(job[_FIELD["qualifications"]]))
    description = "\n\n".join(p for p in (qualifications, responsibilities) if p)

    return {
        "title": title,
        "company": (job[_FIELD["company"]] or "Google").strip(),
        "location": _locations(job[_FIELD["locations"]]),
        "url": JOB_URL.format(job_id=job_id),
        "source": source,
        "work_mode": "",
        "salary": "",
        "season": level_label,
        "description": description,
        "date_scraped": datetime.now(timezone.utc).isoformat(),
    }


def _fetch_page(query: str, location: str, target_level: str, page: int) -> tuple[list, int]:
    """Return ``(jobList, total)`` for one results page, or ``([], 0)`` on failure."""
    params = {"q": query, "page": page}
    if location:
        params["location"] = location
    if target_level:
        params["target_level"] = target_level
    try:
        resp = requests.get(RESULTS_URL, params=params, headers=_HEADERS, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as e:
        logger.error(f"{location or 'anywhere'}/{target_level or 'any'} p{page}: request failed: {e}")
        return [], 0

    m = _DS1_RE.search(resp.text)
    if not m:
        logger.warning(
            f"{location or 'anywhere'}/{target_level or 'any'} p{page}: no ds:1 blob "
            "(page layout may have changed)."
        )
        return [], 0
    try:
        import json

        data = json.loads(m.group(1))
    except ValueError as e:
        logger.error(f"{location}/{target_level} p{page}: ds:1 parse failed: {e}")
        return [], 0

    job_list = data[0] if data else []
    total = int(data[2]) if len(data) > 2 and isinstance(data[2], int) else len(job_list or [])
    return job_list or [], total


def scrape_google_careers(
    queries: list[str] | None = None,
    locations: list[str] | None = None,
    target_levels: list[str] | None = None,
    source: str = "google-careers",
    max_per_query: int = 200,
) -> list[dict]:
    """Scrape Google Careers via its server-rendered results HTML.

    Fans out over ``queries x locations x target_levels`` and pages each combo
    until ``total`` rows are collected (or ``max_per_query`` is hit). Returns
    pipeline-schema job dicts, deduplicated by URL across every combination.

    Args:
        queries: free-text searches (default: ["machine learning"]).
        locations: location filters; ``[""]`` / ``[None]`` means anywhere
            (default: ["United States", "India"]).
        target_levels: Google seniority buckets — EARLY, INTERN_AND_APPRENTICE,
            MID, ADVANCED (default: ["EARLY", "INTERN_AND_APPRENTICE"]).
        source: label stored on each job dict.
        max_per_query: hard per-combination cap on rows collected.
    """
    queries = queries or ["machine learning"]
    locations = locations or ["United States", "India"]
    target_levels = target_levels or ["EARLY", "INTERN_AND_APPRENTICE"]

    jobs_by_url: dict[str, dict] = {}

    for query in queries:
        for location in locations:
            for level in target_levels:
                level_label = _LEVEL_LABELS.get(level, level or "")
                collected = 0
                page = 1
                total = max_per_query
                while collected < min(total, max_per_query):
                    job_list, total = _fetch_page(query, location or "", level, page)
                    if not job_list:
                        break
                    for raw in job_list:
                        job = _normalize(raw, source, level_label)
                        if job:
                            jobs_by_url.setdefault(job["url"], job)
                    collected += len(job_list)
                    logger.info(
                        f"{source}: '{query}' @ {location or 'anywhere'} "
                        f"[{level or 'any'}] {collected}/{total} (page {page})"
                    )
                    page += 1
                    time.sleep(0.4)  # be polite

    jobs = list(jobs_by_url.values())
    logger.info(f"{source}: {len(jobs)} unique jobs collected total.")
    return jobs
