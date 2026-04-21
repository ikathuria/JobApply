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
import re
from datetime import datetime

from playwright.async_api import async_playwright, Page, TimeoutError as PWTimeout

logger = logging.getLogger(__name__)

LOGIN_URL = "https://app.joinhandshake.com/login"
# Landing page after login — clicking Jobs nav reaches the job search
JOBS_BASE_URL = "https://app.joinhandshake.com/jobs"

# Selectors for the search input on the jobs page
_SEARCH_INPUT_SELECTORS = [
    "input[placeholder*='Search']",
    "input[aria-label*='search' i]",
    "input[type='search']",
    "input[data-hook*='search']",
    "input[class*='search' i]",
]

# Job posting URLs always contain /jobs/ or /postings/ followed by a numeric ID
_JOB_URL_PATTERN = re.compile(r"/(jobs|postings)/\d+")


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


async def _type_search(page: Page, query: str) -> bool:
    """Find the search box, type the query, and submit. Returns True on success."""
    for sel in _SEARCH_INPUT_SELECTORS:
        try:
            inp = await page.query_selector(sel)
            if inp:
                await inp.triple_click()           # select-all to clear existing text
                await inp.type(query, delay=60)    # human-ish typing speed
                await asyncio.sleep(0.4)
                await page.keyboard.press("Enter")
                await asyncio.sleep(3)
                return True
        except Exception:
            continue
    return False


async def _extract_job_links(page: Page, seen: set[str], limit: int) -> list[dict]:
    """
    Extract job cards by finding all <a> tags whose href matches a Handshake
    job/posting URL pattern.  Each anchor's closest list item / card container
    is scraped for company + location text.
    """
    date_scraped = datetime.utcnow().isoformat()
    jobs: list[dict] = []

    # Pull all job-link hrefs + surrounding text via a single page.evaluate call
    # (much faster than querying each element individually)
    raw = await page.evaluate(r"""
        () => {
            const results = [];
            const anchors = document.querySelectorAll('a[href]');
            const pattern = /\/(jobs|postings)\/\d+/;
            const seen = new Set();

            for (const a of anchors) {
                const href = a.getAttribute('href') || '';
                if (!pattern.test(href)) continue;
                const url = href.split('?')[0];
                if (seen.has(url)) continue;
                seen.add(url);

                const title = (a.innerText || a.textContent || '').trim();
                if (!title) continue;

                // Walk up to find a card-like container (li or div with role)
                let card = a.closest('li') ||
                           a.closest('[role="listitem"]') ||
                           a.closest('[class*="card" i]') ||
                           a.parentElement;

                const cardText = card ? (card.innerText || '') : '';
                const lines = cardText
                    .split('\n')
                    .map(l => l.trim())
                    .filter(Boolean);

                // Heuristic: company is usually the 2nd distinct non-title line
                // Location usually contains Remote, city, or "United States"
                let company = '';
                let location = '';
                for (const line of lines) {
                    if (line === title) continue;
                    if (!company && line.length < 80 && !/^\$/.test(line)) {
                        company = line;
                        continue;
                    }
                    if (!location && (
                        /remote/i.test(line) ||
                        /united states/i.test(line) ||
                        /,\s+[A-Z]{2}/.test(line) ||
                        /new york|san francisco|chicago|seattle|boston|austin/i.test(line)
                    )) {
                        location = line;
                    }
                }

                results.push({ href, title, company, location });
            }
            return results;
        }
    """)

    for item in raw:
        if len(jobs) >= limit:
            break
        href = item.get("href", "")
        job_url = (
            f"https://app.joinhandshake.com{href}"
            if href.startswith("/") else href
        ).split("?")[0]

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


async def _collect_jobs(page: Page, query: str, limit: int) -> list[dict]:
    logger.info(f"Searching Handshake: '{query}'")

    # Navigate to the jobs landing page
    await page.goto(JOBS_BASE_URL, wait_until="domcontentloaded", timeout=30_000)
    await asyncio.sleep(2)

    # Type into search box (preferred) — falls back to URL param if box not found
    typed = await _type_search(page, query)
    if not typed:
        # Fallback: append query as URL parameter (works on some Handshake versions)
        fallback_url = f"{JOBS_BASE_URL}?query={query.replace(' ', '+')}&job_type=3"
        logger.info(f"Search box not found — trying URL fallback: {fallback_url}")
        await page.goto(fallback_url, wait_until="domcontentloaded", timeout=30_000)
        await asyncio.sleep(3)

    seen: set[str] = set()
    jobs: list[dict] = []
    max_scrolls = 6

    for scroll_round in range(max_scrolls):
        batch = await _extract_job_links(page, seen, limit - len(jobs))
        jobs.extend(batch)
        logger.info(f"  Scroll {scroll_round + 1}/{max_scrolls}: +{len(batch)} → {len(jobs)} total")

        if len(jobs) >= limit:
            break

        # Scroll the result list to trigger lazy-loading
        prev_link_count = len(await page.query_selector_all("a[href]"))
        await page.evaluate("""
            const list = document.querySelector('[class*="result" i], [class*="list" i], main, body');
            if (list) list.scrollTop += 1200;
            window.scrollBy(0, 1200);
        """)
        await asyncio.sleep(2.5)

        new_link_count = len(await page.query_selector_all("a[href]"))
        if new_link_count == prev_link_count and scroll_round > 0:
            logger.info("  No new links after scroll — stopping.")
            break

    logger.info(f"Collected {len(jobs)} jobs for query '{query}'")
    return jobs


def scrape_handshake_sync(
    queries: list[str] | None = None,
    max_jobs: int = 60,
    headless: bool = True,
) -> list[dict]:
    return asyncio.run(scrape_handshake(queries, max_jobs, headless))
