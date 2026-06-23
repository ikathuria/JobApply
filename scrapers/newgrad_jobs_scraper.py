"""
Scraper for newgrad-jobs.com AI/ML new-grad roles.

newgrad-jobs.com embeds the same virtualized jobright.ai table as intern-list.com.
The shared scroll + harvest logic lives in ``scrapers.jobright_minisite``; this
module just pins the embed URL and source label.
"""

from scrapers.jobright_minisite import scrape_minisite

SOURCE_URL = "https://jobright.ai/minisites-jobs/newgrad/us/ml_ai?embed=true"
SOURCE     = "newgrad-jobs.com"


def scrape_newgrad_jobs(max_rows: int = 500) -> list[dict]:
    return scrape_minisite(SOURCE_URL, SOURCE, max_rows)
