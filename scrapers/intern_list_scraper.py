"""
Scraper for intern-list.com AI/ML jobs.
The site embeds a virtualized table from jobright.ai.
We scroll the inner viewport container to progressively reveal all rows,
collecting each unique row (tracked by data-index) as it enters the DOM.
"""

import asyncio
import logging
import re
from datetime import datetime

from playwright.async_api import async_playwright, TimeoutError as PWTimeout

logger = logging.getLogger(__name__)

SOURCE_URL   = "https://jobright.ai/minisites-jobs/intern/us/ml_ai?embed=true"
VIEWPORT_SEL = "div.index_bodyViewport__3xQLm"
ROW_SEL      = "tr.index_tableRow___byxr"
COUNT_SEL    = "span.index_recordCount__iL4yH"

TITLE_SEL   = "span.index_positionTitle__xrG_i"
LINK_SEL    = "a.index_airtableApplyLink__Dob0_"
MODE_SEL    = "td:nth-child(5) .ant-tag"
LOC_SEL     = "td:nth-child(6) span.index_cellText__hfa_t"
COMPANY_SEL = "td:nth-child(7) span.index_cellText__hfa_t"
SALARY_SEL  = "td:nth-child(8) span.index_cellText__hfa_t"
SEASON_SEL  = "td:nth-child(9) span.index_cellText__hfa_t"
QUALS_SEL   = "div.index_qualificationsContent__4kAgd"


async def _parse_row(row) -> dict | None:
    """Extract all fields from a visible table row."""
    async def txt(sel):
        el = await row.query_selector(sel)
        return (await el.inner_text()).strip() if el else ""

    async def href(sel):
        el = await row.query_selector(sel)
        return (await el.get_attribute("href") or "").strip() if el else ""

    title   = await txt(TITLE_SEL)
    url     = await href(LINK_SEL)
    if not title or not url:
        return None

    return {
        "title":        title,
        "company":      await txt(COMPANY_SEL),
        "location":     await txt(LOC_SEL),
        "url":          url,
        "source":       "intern-list.com",
        "work_mode":    await txt(MODE_SEL),
        "salary":       await txt(SALARY_SEL),
        "season":       await txt(SEASON_SEL),
        "description":  await txt(QUALS_SEL),
        "date_scraped": datetime.utcnow().isoformat(),
    }


async def _scrape(max_rows: int = 500) -> list[dict]:
    jobs_by_idx: dict[str, dict] = {}  # data-index -> job dict

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(
            viewport={"width": 1280, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
        )

        logger.info("Loading jobright.ai AI/ML intern listings...")
        await page.goto(SOURCE_URL, wait_until="load", timeout=45_000)
        await asyncio.sleep(4)

        try:
            await page.wait_for_selector(ROW_SEL, timeout=20_000)
        except PWTimeout:
            logger.error("Timed out waiting for job rows.")
            await browser.close()
            return []

        # Read total record count from the page
        total = max_rows
        count_el = await page.query_selector(COUNT_SEL)
        if count_el:
            count_text = await count_el.inner_text()
            m = re.search(r"(\d+)", count_text.replace(",", ""))
            if m:
                total = min(int(m.group(1)), max_rows)
                logger.info(f"Total records available: {int(m.group(1))}, collecting up to {total}")

        async def harvest():
            """Parse all currently visible rows and store by data-index."""
            rows = await page.query_selector_all(ROW_SEL)
            for row in rows:
                idx = await row.get_attribute("data-index")
                if idx is None or idx in jobs_by_idx:
                    continue
                job = await _parse_row(row)
                if job:
                    jobs_by_idx[idx] = job

        await harvest()
        logger.info(f"Initial harvest: {len(jobs_by_idx)} rows")

        # Scroll the virtualized viewport container to load more rows
        stale_rounds = 0
        while len(jobs_by_idx) < total:
            prev = len(jobs_by_idx)

            await page.evaluate(f'''
                const vp = document.querySelector("{VIEWPORT_SEL}");
                if (vp) vp.scrollTop += 600;
            ''')
            await asyncio.sleep(1.2)
            await harvest()

            gained = len(jobs_by_idx) - prev
            logger.info(f"Scroll step: {len(jobs_by_idx)}/{total} rows collected (+{gained})")

            if gained == 0:
                stale_rounds += 1
                if stale_rounds >= 4:
                    logger.info("No new rows after 4 consecutive scrolls — stopping.")
                    break
            else:
                stale_rounds = 0

        await browser.close()

    jobs = list(jobs_by_idx.values())
    logger.info(f"intern-list.com: {len(jobs)} jobs collected total.")
    return jobs


def scrape_intern_list(max_rows: int = 500) -> list[dict]:
    return asyncio.run(_scrape(max_rows))
