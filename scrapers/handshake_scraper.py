"""
Handshake scraper using Playwright.
Logs into app.joinhandshake.com with university credentials,
searches for AI/ML internships, and collects listings.

Requires env vars:
  HANDSHAKE_EMAIL     – your university email
  HANDSHAKE_PASSWORD  – your Handshake password
"""

import asyncio
import logging
import os
from datetime import datetime

from playwright.async_api import async_playwright, Page, TimeoutError as PWTimeout

logger = logging.getLogger(__name__)

LOGIN_URL = "https://app.joinhandshake.com/login"
# job_type=3 = Internship; sorted by recent; work_study_required=false
JOBS_URL  = (
    "https://app.joinhandshake.com/stu/postings"
    "?job_type=3&work_study_required=false&sort_direction=desc&sort_column=created_at"
)

# Selectors — Handshake uses data-hook attrs which are more stable than class names
_CARD_SELECTORS = [
    "[data-hook='job-card']",
    "li[class*='posting-list']",
    "li[class*='job-card']",
    "div[class*='JobCard']",
]
_TITLE_SELECTORS = [
    "[data-hook='jobs-card-title']",
    "a[data-hook='job-card-title-link']",
    "a[class*='job-title']",
    "a[class*='JobCard__title']",
]
_COMPANY_SELECTORS = [
    "[data-hook='job-card-employer-name']",
    "[data-hook='job-card-employer']",
    "span[class*='employer-name']",
    "span[class*='JobCard__employer']",
]
_LOCATION_SELECTORS = [
    "[data-hook='job-card-location']",
    "span[class*='location']",
    "div[class*='JobCard__location']",
]


async def _first_text(el, selectors: list[str]) -> str:
    for sel in selectors:
        child = await el.query_selector(sel)
        if child:
            try:
                return (await child.inner_text()).strip()
            except Exception:
                continue
    return ""


async def _first_href(el, selectors: list[str]) -> str:
    for sel in selectors:
        child = await el.query_selector(sel)
        if child:
            try:
                href = await child.get_attribute("href") or ""
                return href.strip()
            except Exception:
                continue
    return ""


async def _find_cards(page: Page):
    for sel in _CARD_SELECTORS:
        cards = await page.query_selector_all(sel)
        if cards:
            return cards
    return []


async def scrape_handshake(
    queries: list[str] | None = None,
    max_jobs: int = 60,
    headless: bool = True,
) -> list[dict]:
    """
    Log into Handshake and collect AI/ML internship listings.
    Returns a list of job dicts.
    """
    email    = os.getenv("HANDSHAKE_EMAIL", "")
    password = os.getenv("HANDSHAKE_PASSWORD", "")

    if not email or not password:
        logger.error("HANDSHAKE_EMAIL and HANDSHAKE_PASSWORD must be set in .env / GHA secrets.")
        return []

    if queries is None:
        queries = ["AI intern", "machine learning intern", "LLM intern", "data science intern"]

    jobs: dict[str, dict] = {}  # url -> job dict (dedupe by URL)

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=headless,
            args=["--no-sandbox", "--disable-dev-shm-usage"] if headless else [],
            slow_mo=40,
        )
        context = await browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
        )
        page = await context.new_page()

        try:
            if not await _login(page, email, password):
                return []

            for query in queries:
                if len(jobs) >= max_jobs:
                    break
                found = await _collect_jobs(page, query, max_jobs - len(jobs))
                for j in found:
                    if j["url"] not in jobs:
                        jobs[j["url"]] = j
                logger.info(f"After query '{query}': {len(jobs)} unique jobs total")

        except Exception as e:
            logger.error(f"Handshake scraper error: {e}", exc_info=True)
        finally:
            await browser.close()

    result = list(jobs.values())
    logger.info(f"Handshake scraping complete: {len(result)} jobs found.")
    return result


async def _login(page: Page, email: str, password: str) -> bool:
    logger.info("Navigating to Handshake login...")
    await page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=30_000)
    await asyncio.sleep(2)

    # Handshake shows a school search first — enter email to pick university SSO
    # or use direct email/password login
    try:
        # Try the "Sign in with email" path first
        email_btn = await page.query_selector("a[href*='email']")
        if email_btn:
            await email_btn.click()
            await asyncio.sleep(1)
    except Exception:
        pass

    try:
        await page.fill("input[type='email'], input[name='email'], #email", email, timeout=8_000)
        await asyncio.sleep(0.5)

        # Some Handshake flows show password on the same page, others after clicking Next
        next_btn = await page.query_selector("button[type='submit'], input[type='submit']")
        if next_btn:
            await next_btn.click()
            await asyncio.sleep(2)

        await page.fill("input[type='password'], input[name='password'], #password", password, timeout=8_000)
        await asyncio.sleep(0.5)

        submit = await page.query_selector("button[type='submit'], input[type='submit']")
        if submit:
            await submit.click()

        # Wait for dashboard / student landing page
        try:
            await page.wait_for_url("**/stu/**", timeout=30_000)
            logger.info("Handshake login successful.")
            return True
        except PWTimeout:
            # Check if we're still on a recognisable post-login page
            current = page.url
            if "handshake" in current and "login" not in current:
                logger.info(f"Handshake: landed on {current} — assuming logged in.")
                return True
            logger.error(f"Handshake login failed — still at: {current}")
            return False

    except Exception as e:
        logger.error(f"Handshake login error: {e}")
        return False


async def _collect_jobs(page: Page, query: str, limit: int) -> list[dict]:
    url = f"{JOBS_URL}&query={query.replace(' ', '+')}"
    logger.info(f"Searching Handshake: '{query}'")

    await page.goto(url, wait_until="domcontentloaded", timeout=30_000)
    await asyncio.sleep(3)

    jobs = []
    date_scraped = datetime.utcnow().isoformat()
    scroll_rounds = 0
    max_scrolls = 8

    while len(jobs) < limit and scroll_rounds < max_scrolls:
        cards = await _find_cards(page)
        if not cards:
            logger.warning(f"No job cards found on Handshake for query '{query}' — page may need login refresh.")
            break

        for card in cards:
            if len(jobs) >= limit:
                break
            try:
                title    = await _first_text(card, _TITLE_SELECTORS)
                company  = await _first_text(card, _COMPANY_SELECTORS)
                location = await _first_text(card, _LOCATION_SELECTORS)
                href     = await _first_href(card, _TITLE_SELECTORS)

                if not title or not href:
                    continue

                job_url = (
                    f"https://app.joinhandshake.com{href}"
                    if href.startswith("/") else href
                ).split("?")[0]

                # Skip duplicates within this query pass
                if any(j["url"] == job_url for j in jobs):
                    continue

                jobs.append({
                    "title":        title,
                    "company":      company,
                    "location":     location,
                    "url":          job_url,
                    "source":       "handshake",
                    "easy_apply":   False,
                    "date_scraped": date_scraped,
                })

            except Exception as e:
                logger.debug(f"Handshake card parse error: {e}")
                continue

        # Scroll to load more
        prev_count = len(jobs)
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await asyncio.sleep(2.5)
        scroll_rounds += 1

        # Stop if no new jobs appeared after scroll
        cards_after = await _find_cards(page)
        if len(cards_after) == len(cards):
            break

    logger.info(f"Collected {len(jobs)} jobs for query '{query}'")
    return jobs


def scrape_handshake_sync(
    queries: list[str] | None = None,
    max_jobs: int = 60,
    headless: bool = True,
) -> list[dict]:
    return asyncio.run(scrape_handshake(queries, max_jobs, headless))
