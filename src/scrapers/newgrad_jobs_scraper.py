"""
Scraper for newgrad-jobs.com new-grad roles.

newgrad-jobs.com embeds the same virtualized jobright.ai table as intern-list.com.
The shared JSON-API client lives in ``scrapers.jobright_minisite``; this module
pins the source label and which minisite verticals to pull — one per resume track
(``ml_ai``, ``swe``, ``data_science``, ``data_analysis``; slugs verified 2026-10-19).
"""

from scrapers.jobright_minisite import scrape_minisite

SOURCE = "newgrad-jobs.com"
DEFAULT_VERTICALS = ("ml_ai",)


def scrape_newgrad_jobs(max_rows: int = 500, verticals=DEFAULT_VERTICALS) -> list[dict]:
    """Up to ``max_rows`` per vertical, deduplicated by URL across verticals."""
    by_url: dict[str, dict] = {}
    for vertical in verticals:
        for job in scrape_minisite(f"newgrad:us:{vertical}", SOURCE, max_rows):
            by_url.setdefault(job["url"], job)
    return list(by_url.values())
