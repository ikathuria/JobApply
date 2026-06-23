"""
Scraper for newgrad-jobs.com AI/ML new-grad roles.

newgrad-jobs.com embeds the same virtualized jobright.ai table as intern-list.com.
The shared JSON-API client lives in ``scrapers.jobright_minisite``; this module
just pins the minisite category slug and source label.
"""

from scrapers.jobright_minisite import scrape_minisite

CATEGORY = "newgrad:us:ml_ai"
SOURCE   = "newgrad-jobs.com"


def scrape_newgrad_jobs(max_rows: int = 500) -> list[dict]:
    return scrape_minisite(CATEGORY, SOURCE, max_rows)
