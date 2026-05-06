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
    await page.goto(LINKEDIN_LOGIN_URL, wait_until="domcontentloaded")
    await asyncio.sleep(2)

    await asyncio.sleep(3)  # let React finish rendering

    async def fill_first_visible(selectors: list[str], value: str):
        for sel in selectors:
            for el in await page.query_selector_all(sel):
                if await el.is_visible():
                    await el.fill(value)
                    return el
        return None

    await fill_first_visible(["input[type='email']", "#username"], email)
    await asyncio.sleep(0.5)

    pass_el = await fill_first_visible(["input[type='password']", "#password"], password)
    await asyncio.sleep(0.3)

    submit = await page.query_selector(
        "button[data-litms-control-urn='login-submit'], "
        "form.login__form button[type='submit']"
    )
    if submit:
        await submit.click()
    elif pass_el:
        await pass_el.press("Enter")

    try:
        await page.wait_for_url("**/feed/**", timeout=60_000)
        logger.info("LinkedIn login successful.")
    except PWTimeout:
        logger.warning(
            "LinkedIn login redirect timed out — if 2FA/challenge appeared, "
            "complete it in the browser window. Waiting 30s..."
        )
        await asyncio.sleep(30)


CARD_SELECTORS = [
    "li[data-occludable-job-id]",
    "li.scaffold-layout__list-item",
    "li.jobs-search-results__list-item",
]

TITLE_SELECTORS = [
    "a.job-card-list__title--link",
    "a.job-card-list__title",
    "a[data-control-name='jobcard_title']",
]

COMPANY_SELECTORS = [
    "span.job-card-container__primary-description",
    ".job-card-container__company-name",
    ".artdeco-entity-lockup__subtitle span",
    ".artdeco-entity-lockup__subtitle",
]

LOCATION_SELECTORS = [
    "li.job-card-container__metadata-item",
    ".job-card-container__metadata-item",
    ".artdeco-entity-lockup__caption",
]


async def _first_match(el, selectors):
    for sel in selectors:
        found = await el.query_selector(sel)
        if found:
            return found
    return None


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
        "f_JT": "I",         # Internship job type
        "f_TPR": "r2592000", # Past 30 days (was r604800/1 week — too narrow)
        "sortBy": "DD",      # Date descending
    }
    if easy_apply_only:
        params["f_LF"] = "f_AL"  # Easy Apply filter

    query_string = "&".join(f"{k}={v}" for k, v in params.items())
    url = f"{LINKEDIN_JOBS_URL}?{query_string}"

    await page.goto(url, wait_until="domcontentloaded")
    await asyncio.sleep(4)

    current_url = page.url
    logger.info(f"Job search landed on: {current_url}")

    jobs = []
    date_scraped = datetime.utcnow().isoformat()
    seen_urls = set()
    stall_count = 0

    while len(jobs) < max_jobs:
        # Try each card selector until one returns results
        job_cards = []
        for sel in CARD_SELECTORS:
            job_cards = await page.query_selector_all(sel)
            if job_cards:
                logger.debug(f"Card selector '{sel}' matched {len(job_cards)} cards")
                break

        if not job_cards:
            logger.warning("No job cards found with any known selector — dumping visible text sample")
            try:
                sample = await page.evaluate("() => document.body.innerText.slice(0, 500)")
                logger.warning(f"Page text sample: {sample!r}")
            except Exception:
                pass
            break

        prev_len = len(jobs)
        for card in job_cards:
            if len(jobs) >= max_jobs:
                break
            try:
                title_el   = await _first_match(card, TITLE_SELECTORS)
                company_el = await _first_match(card, COMPANY_SELECTORS)
                loc_el     = await _first_match(card, LOCATION_SELECTORS)

                title   = (await title_el.inner_text()).strip()   if title_el   else ""
                company = (await company_el.inner_text()).strip() if company_el else ""
                loc     = (await loc_el.inner_text()).strip()     if loc_el     else ""
                href    = await title_el.get_attribute("href")    if title_el   else ""

                if not title or not href:
                    continue

                job_url = f"https://www.linkedin.com{href}" if href.startswith("/") else href
                job_url = job_url.split("?")[0]

                if job_url in seen_urls:
                    continue
                seen_urls.add(job_url)

                jobs.append({
                    "title": title,
                    "company": company,
                    "location": loc,
                    "url": job_url,
                    "source": "linkedin",
                    "easy_apply": easy_apply_only,
                    "date_scraped": date_scraped,
                })

            except Exception as e:
                logger.debug(f"Error parsing job card: {e}")
                continue

        logger.info(f"Collected {len(jobs)} LinkedIn jobs so far...")

        if len(jobs) == prev_len:
            stall_count += 1
            if stall_count >= 2:
                break
        else:
            stall_count = 0

        loaded = await _load_more(page)
        if not loaded:
            break

        await asyncio.sleep(2)

    logger.info(f"LinkedIn scraping complete: {len(jobs)} jobs found.")
    return jobs


async def _load_more(page: Page) -> bool:
    """Scroll to trigger infinite scroll. Returns False if no new cards appeared."""
    prev_count = 0
    for sel in CARD_SELECTORS:
        cards = await page.query_selector_all(sel)
        if cards:
            prev_count = len(cards)
            break

    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    await asyncio.sleep(2)

    # try clicking 'See more jobs' button if present
    for btn_sel in [
        "button.infinite-scroller__show-more-button",
        "button[aria-label='See more jobs']",
        "button.scaffold-finite-scroll__load-button",
    ]:
        see_more = await page.query_selector(btn_sel)
        if see_more:
            try:
                await see_more.click()
                await asyncio.sleep(2)
            except Exception:
                pass
            break

    new_count = 0
    for sel in CARD_SELECTORS:
        cards = await page.query_selector_all(sel)
        if cards:
            new_count = len(cards)
            break

    return new_count > prev_count


def scrape_linkedin_sync(
    query: str = "AI ML internship",
    location: str = "United States",
    easy_apply_only: bool = True,
    max_jobs: int = 50,
    headless: bool = False,
) -> list[dict]:
    return asyncio.run(scrape_linkedin(query, location, easy_apply_only, max_jobs, headless))
