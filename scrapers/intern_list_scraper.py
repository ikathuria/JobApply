"""
Scraper for intern-list.com AI/ML internships.

intern-list.com embeds a virtualized jobright.ai table. The shared JSON-API
client lives in ``scrapers.jobright_minisite``; this module just pins the minisite
category slug and source label.
"""

from scrapers.jobright_minisite import scrape_minisite

CATEGORY = "intern:us:ml_ai"
SOURCE   = "intern-list.com"


def scrape_intern_list(max_rows: int = 500) -> list[dict]:
    return scrape_minisite(CATEGORY, SOURCE, max_rows)
