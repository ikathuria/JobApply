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
import urllib.parse
from datetime import datetime

from playwright.async_api import async_playwright, Page, TimeoutError as PWTimeout

logger = logging.getLogger(__name__)

LOGIN_URL = "https://app.joinhandshake.com/login"

# Base search URL with filters pre-set:
#   jobType=3          → internships only
#   salaryType=1       → paid only
#   workAuthorization  → includes OPT/CPT/visa-sponsorship/no-US-required
#   sort=posted_date_desc
_SEARCH_BASE = (
    "https://app.joinhandshake.com/job-search"
    "?pay%5BsalaryType%5D=1"
    "&jobType=3"
    "&workAuthorization=openToUSVisaSponsorship"
    "&workAuthorization=openToOptionalPracticalTraining"
    "&workAuthorization=openToCurricularPracticalTraining"
    "&workAuthorization=noUSWork"
    "&workAuthorization=workAuthNotSpecified"
    "&sort=posted_date_desc"
    "&per_page=25"
)


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
    """
    Handshake login flow (as of 2026):
      1. Enter email → Tab away to activate Next button → click Next
      2. "Get connected" SSO screen appears → click "Log in another way"
      3. Enter password → submit
    """
    logger.info("Navigating to Handshake login...")
    await page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=30_000)
    await asyncio.sleep(2)

    try:
        # ── Step 1: fill email field ──────────────────────────────────────────
        email_sel = "input[type='email'], input[name='email'], #email"
        await page.wait_for_selector(email_sel, timeout=10_000)
        await page.fill(email_sel, email)
        await asyncio.sleep(0.3)

        # Tab away — this triggers the field's blur handler which activates Next
        await page.keyboard.press("Tab")
        await asyncio.sleep(0.8)

        # Click the Next / Continue button
        next_btn = await page.query_selector(
            "button[type='submit'], input[type='submit'], button:has-text('Next'), button:has-text('Continue')"
        )
        if next_btn:
            await next_btn.click()
        else:
            await page.keyboard.press("Enter")
        logger.info("Handshake: submitted email, waiting for SSO screen...")
        await asyncio.sleep(3)

        # ── Step 2: "Get connected" SSO screen ───────────────────────────────
        # Look for "Log in another way" link/button to bypass university SSO
        alt_login = await page.query_selector(
            "button:has-text('Log in another way'), "
            "a:has-text('Log in another way'), "
            "button:has-text('another way'), "
            "a:has-text('another way')"
        )
        if alt_login:
            logger.info("Handshake: clicking 'Log in another way' to use email/password...")
            await alt_login.click()
            await asyncio.sleep(2)
        else:
            logger.info("Handshake: no SSO intercept found — proceeding directly to password.")

        # ── Step 3: fill password ─────────────────────────────────────────────
        pw_sel = "input[type='password'], input[name='password'], #password"
        await page.wait_for_selector(pw_sel, timeout=10_000)
        await page.fill(pw_sel, password)
        await asyncio.sleep(0.3)

        await page.keyboard.press("Tab")   # activate submit button
        await asyncio.sleep(0.4)

        submit = await page.query_selector(
            "button[type='submit'], input[type='submit'], button:has-text('Sign in'), button:has-text('Log in')"
        )
        if submit:
            await submit.click()
        else:
            await page.keyboard.press("Enter")

        logger.info("Handshake: submitted password, waiting for redirect...")

        # ── Step 4: confirm login ─────────────────────────────────────────────
        try:
            await page.wait_for_url("**/stu/**", timeout=30_000)
            logger.info("Handshake login successful.")
            return True
        except PWTimeout:
            current = page.url
            if "handshake" in current and "login" not in current:
                logger.info(f"Handshake: landed on {current} — assuming logged in.")
                return True
            logger.error(f"Handshake login failed — still at: {current}")
            return False

    except Exception as e:
        logger.error(f"Handshake login error: {e}", exc_info=True)
        return False


async def _extract_cards(page: Page, seen: set[str], limit: int) -> list[dict]:
    """
    Extract job cards from the current Handshake job-search page.

    Handshake card DOM (confirmed from live page dump):
      <div data-hook="job-result-card | 10913952" ...>
        <a href="/job-search/10913952?..." aria-label="View Applied AI Intern">
        <span class="sc-djhChl ...">Company Name</span>   ← first styled span = company
        <div data-hook="job-result-card-footer">
          <span class="sc-cfpDJx ...">Lisle, IL</span>    ← location in footer
        </div>
      </div>

    Canonical job URL: https://app.joinhandshake.com/jobs/{id}
    """
    date_scraped = datetime.utcnow().isoformat()

    raw: list[dict] = await page.evaluate("""
        () => {
            const results = [];
            // Cards have data-hook="job-result-card | <id>"
            const cards = document.querySelectorAll('[data-hook^="job-result-card |"]');

            for (const card of cards) {
                // Extract numeric job ID from data-hook attribute
                const hookVal = card.getAttribute('data-hook') || '';
                const idMatch = hookVal.match(/\\|\\s*(\\d+)/);
                if (!idMatch) continue;
                const jobId = idMatch[1];

                // Title lives in aria-label="View <Job Title>" on the card's <a>
                const anchor = card.querySelector('a[aria-label^="View "]');
                if (!anchor) continue;
                const title = anchor.getAttribute('aria-label').replace(/^View\\s+/, '').trim();
                if (!title) continue;

                // Company: first span with a styled class inside the card
                // (Handshake uses generated class names like sc-djhChl)
                let company = '';
                const companyEl = card.querySelector('a[aria-label^="View "] ~ * span, span[class*="sc-"]');
                if (companyEl) company = companyEl.innerText.trim();

                // Location: span inside the card footer
                let location = '';
                const footer = card.querySelector('[data-hook="job-result-card-footer"]');
                if (footer) {
                    const locEl = footer.querySelector('span');
                    if (locEl) location = locEl.innerText.trim();
                }

                results.push({ jobId, title, company, location });
            }
            return results;
        }
    """)

    jobs: list[dict] = []
    for item in raw:
        if len(jobs) >= limit:
            break
        job_url = f"https://app.joinhandshake.com/jobs/{item['jobId']}"
        if job_url in seen:
            continue
        seen.add(job_url)
        jobs.append({
            "title":        item["title"],
            "company":      item.get("company", ""),
            "location":     item.get("location", ""),
            "url":          job_url,
            "source":       "handshake",
            "easy_apply":   False,
            "date_scraped": date_scraped,
        })
    return jobs


async def _wait_for_cards(page: Page, timeout: float = 15.0) -> bool:
    """Wait until at least one job card appears on the page."""
    try:
        await page.wait_for_selector(
            '[data-hook^="job-result-card |"]',
            timeout=int(timeout * 1000),
        )
        return True
    except PWTimeout:
        logger.warning("Timed out waiting for job cards.")
        return False


async def _collect_jobs(page: Page, query: str, limit: int) -> list[dict]:
    """
    Navigate to Handshake job search with the given query and collect up to
    `limit` job listings by paginating through result pages.
    """
    logger.info(f"Searching Handshake: '{query}'")

    encoded_query = urllib.parse.quote(query)
    search_url = f"{_SEARCH_BASE}&query={encoded_query}&page=1"

    await page.goto(search_url, wait_until="domcontentloaded", timeout=30_000)
    await asyncio.sleep(2)

    if not await _wait_for_cards(page):
        logger.warning(f"No job cards found for query '{query}' — page may have changed.")
        return []

    seen: set[str] = set()
    jobs: list[dict] = []
    page_num = 1

    while len(jobs) < limit:
        batch = await _extract_cards(page, seen, limit - len(jobs))
        jobs.extend(batch)
        logger.info(f"  Page {page_num}: +{len(batch)} → {len(jobs)} total")

        if len(jobs) >= limit or not batch:
            break

        # Try to click the next page button
        page_num += 1
        next_btn = await page.query_selector(f'button[value="{page_num}"]')
        if not next_btn:
            # Also try an explicit "next" arrow button
            next_btn = await page.query_selector(
                'button[aria-label="Next page"], button[aria-label="next"]'
            )
        if not next_btn:
            logger.info("  No more pages found.")
            break

        await next_btn.click()
        await asyncio.sleep(2.5)
        await _wait_for_cards(page, timeout=10)

    logger.info(f"Collected {len(jobs)} jobs for query '{query}'")
    return jobs


def scrape_handshake_sync(
    queries: list[str] | None = None,
    max_jobs: int = 60,
    headless: bool = True,
) -> list[dict]:
    return asyncio.run(scrape_handshake(queries, max_jobs, headless))
