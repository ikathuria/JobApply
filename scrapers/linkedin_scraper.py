"""
LinkedIn scraper using Playwright.
Logs in as the user, searches for AI/ML internships, and collects Easy Apply listings.
Operates as a real browser session — not raw scraping.
"""

import asyncio
import logging
import os
from datetime import datetime

from playwright.async_api import async_playwright, Page, TimeoutError as PWTimeout

logger = logging.getLogger(__name__)

LINKEDIN_LOGIN_URL = "https://www.linkedin.com/login"
LINKEDIN_JOBS_URL = "https://www.linkedin.com/jobs/search/"


async def scrape_linkedin(
    query: str = "AI ML internship",
    location: str = "United States",
    easy_apply_only: bool = True,
    max_jobs: int = 50,
    headless: bool = False,
) -> list[dict]:
    """
    Log into LinkedIn and collect job listings matching the query.
    headless=False lets you watch and handle any CAPTCHA/2FA manually.
    Returns list of job dicts.
    """
    email = os.getenv("LINKEDIN_EMAIL", "")
    password = os.getenv("LINKEDIN_PASSWORD", "")

    if not email or not password:
        logger.error("LINKEDIN_EMAIL and LINKEDIN_PASSWORD must be set in .env")
        return []

    jobs = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless, slow_mo=50)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
        )
        page = await context.new_page()

        try:
            await _login(page, email, password)
            jobs = await _search_jobs(page, query, location, easy_apply_only, max_jobs)
        except Exception as e:
            logger.error(f"LinkedIn scraper error: {e}")
        finally:
            await browser.close()

    return jobs


async def _login(page: Page, email: str, password: str) -> None:
    logger.info("Logging into LinkedIn...")
    await page.goto(LINKEDIN_LOGIN_URL, wait_until="networkidle")

    await page.fill("#username", email)
    await page.fill("#password", password)
    await page.click("button[type='submit']")

    try:
        # wait for redirect to feed — if 2FA appears, user handles it in the browser window
        await page.wait_for_url("**/feed/**", timeout=60_000)
        logger.info("LinkedIn login successful.")
    except PWTimeout:
        logger.warning(
            "LinkedIn login redirect timed out — if 2FA appeared, "
            "complete it in the browser window. Waiting 30s..."
        )
        await asyncio.sleep(30)


async def _search_jobs(
    page: Page,
    query: str,
    location: str,
    easy_apply_only: bool,
    max_jobs: int,
) -> list[dict]:
    logger.info(f"Searching LinkedIn jobs: '{query}' in '{location}'")

    params = {
        "keywords": query,
        "location": location,
        "f_JT": "I",      # Internship job type
        "f_TPR": "r604800",  # Past week
        "sortBy": "DD",    # Date descending
    }
    if easy_apply_only:
        params["f_LF"] = "f_AL"  # Easy Apply filter

    query_string = "&".join(f"{k}={v}" for k, v in params.items())
    url = f"{LINKEDIN_JOBS_URL}?{query_string}"

    await page.goto(url, wait_until="domcontentloaded")
    await asyncio.sleep(3)

    jobs = []
    date_scraped = datetime.utcnow().isoformat()
    seen_urls = set()

    while len(jobs) < max_jobs:
        job_cards = await page.query_selector_all("li.jobs-search-results__list-item")

        for card in job_cards:
            if len(jobs) >= max_jobs:
                break

            try:
                title_el = await card.query_selector("a.job-card-list__title, a[data-control-name='jobcard_title']")
                company_el = await card.query_selector(".job-card-container__company-name, .artdeco-entity-lockup__subtitle")
                location_el = await card.query_selector(".job-card-container__metadata-item, .artdeco-entity-lockup__caption")

                title = (await title_el.inner_text()).strip() if title_el else ""
                company = (await company_el.inner_text()).strip() if company_el else ""
                location = (await location_el.inner_text()).strip() if location_el else ""
                href = await title_el.get_attribute("href") if title_el else ""

                if not title or not href:
                    continue

                job_url = f"https://www.linkedin.com{href}" if href.startswith("/") else href
                job_url = job_url.split("?")[0]  # strip tracking params

                if job_url in seen_urls:
                    continue
                seen_urls.add(job_url)

                jobs.append({
                    "title": title,
                    "company": company,
                    "location": location,
                    "url": job_url,
                    "source": "linkedin",
                    "easy_apply": easy_apply_only,
                    "date_scraped": date_scraped,
                })

            except Exception as e:
                logger.debug(f"Error parsing job card: {e}")
                continue

        logger.info(f"Collected {len(jobs)} LinkedIn jobs so far...")

        # scroll to load more
        loaded = await _load_more(page)
        if not loaded:
            break

        await asyncio.sleep(2)

    logger.info(f"LinkedIn scraping complete: {len(jobs)} jobs found.")
    return jobs


async def _load_more(page: Page) -> bool:
    """Scroll down to trigger infinite scroll. Returns False if no new content."""
    prev_count = len(await page.query_selector_all("li.jobs-search-results__list-item"))

    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    await asyncio.sleep(2)

    # try clicking 'See more jobs' button if present
    see_more = await page.query_selector("button.infinite-scroller__show-more-button")
    if see_more:
        try:
            await see_more.click()
            await asyncio.sleep(2)
        except Exception:
            pass

    new_count = len(await page.query_selector_all("li.jobs-search-results__list-item"))
    return new_count > prev_count


def scrape_linkedin_sync(
    query: str = "AI ML internship",
    location: str = "United States",
    easy_apply_only: bool = True,
    max_jobs: int = 50,
    headless: bool = False,
) -> list[dict]:
    return asyncio.run(scrape_linkedin(query, location, easy_apply_only, max_jobs, headless))
