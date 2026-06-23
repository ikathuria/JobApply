"""
Scraper for intern-list.com AI/ML internships.

intern-list.com embeds a virtualized table from jobright.ai. The shared scroll +
harvest logic lives in ``scrapers.jobright_minisite``; this module just pins the
embed URL and source label.
"""

from scrapers.jobright_minisite import scrape_minisite

SOURCE_URL = "https://jobright.ai/minisites-jobs/intern/us/ml_ai?embed=true"
SOURCE     = "intern-list.com"


def scrape_intern_list(max_rows: int = 500) -> list[dict]:
    return scrape_minisite(SOURCE_URL, SOURCE, max_rows)
