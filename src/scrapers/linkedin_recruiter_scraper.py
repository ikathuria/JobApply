"""
LinkedIn recruiter scraper using Playwright.

Reuses the same logged-in LinkedIn session as linkedin_scraper to search People
by company + recruiter-style titles, collecting recruiter / talent-acquisition
contacts (name, title, company, profile URL).

LinkedIn People search does NOT expose email addresses — resolve those separately
via pipeline.email_finder. This scraper only captures the public profile fields.

People search is the most rate-limit / checkpoint-prone surface on LinkedIn, so we
pace conservatively between companies and cap results per company. Run headed
locally (headless=False) so you can clear any checkpoint by hand.
"""

import asyncio
import logging
from urllib.parse import quote_plus

from playwright.async_api import async_playwright, Page

# Reuse the exact login flow the job scraper uses.
from scrapers.linkedin_scraper import _login

logger = logging.getLogger(__name__)

PEOPLE_SEARCH_URL = "https://www.linkedin.com/search/results/people/"

# Default recruiter-style titles to search for and to filter result subtitles by.
DEFAULT_TITLES = [
    "recruiter",
    "technical recruiter",
    "talent acquisition",
    "university recruiter",
    "campus recruiter",
    "sourcer",
    "talent partner",
]

# A result is kept only if its subtitle contains one of these (when a subtitle was
# parsed). Keeps the obvious recruiters and drops random employees the keyword
# search drags in.
_RECRUITER_HINTS = (
    "recruit", "talent", "sourcer", "sourcing", "people", "hr ",
    "human resources", "campus", "university", "hiring",
)

# Result-card containers, profile links, and subtitles — LinkedIn rotates these
# class names, so each is a best-effort list tried in order (mirrors the job
# scraper's resilience pattern).
RESULT_SELECTORS = [
    "li.reusable-search__result-container",
    "div.entity-result__item",
    "li.org-people-profile-card__profile-card-spacing",
    "div.entity-result",
]
SUBTITLE_SELECTORS = [
    "div.entity-result__primary-subtitle",
    ".entity-result__primary-subtitle",
    ".artdeco-entity-lockup__subtitle",
]


def _normalize_profile_url(href: str) -> str:
    """Strip query/fragment and trailing slash from a /in/ profile URL."""
    url = href.split("?")[0].split("#")[0].rstrip("/")
    if url.startswith("/"):
        url = f"https://www.linkedin.com{url}"
    return url


def _looks_like_recruiter(subtitle: str) -> bool:
    s = (subtitle or "").lower()
    if not s:
        return True  # no subtitle parsed — trust the keyword search, keep it
    return any(h in s for h in _RECRUITER_HINTS)


async def _parse_people(page: Page, company: str, max_results: int) -> list[dict]:
    """Parse visible people cards into recruiter dicts, de-duped by profile URL."""
    cards = []
    for sel in RESULT_SELECTORS:
        cards = await page.query_selector_all(sel)
        if cards:
            logger.debug(f"People selector '{sel}' matched {len(cards)} cards")
            break

    recruiters: list[dict] = []
    seen: set[str] = set()

    for card in cards:
        if len(recruiters) >= max_results:
            break
        try:
            link = await card.query_selector("a[href*='/in/']")
            if not link:
                continue
            href = await link.get_attribute("href") or ""
            if "/in/" not in href:
                continue
            profile_url = _normalize_profile_url(href)
            if profile_url in seen:
                continue

            # Name lives in a hidden span inside the link on most layouts.
            name = ""
            name_el = await link.query_selector("span[aria-hidden='true']")
            if name_el:
                name = (await name_el.inner_text()).strip()
            if not name:
                name = (await link.inner_text()).strip()
            # Drop LinkedIn noise like "View X's profile" / connection-degree text.
            name = name.splitlines()[0].strip()
            if not name or name.lower().startswith("linkedin member"):
                continue

            subtitle = ""
            for sub_sel in SUBTITLE_SELECTORS:
                sub_el = await card.query_selector(sub_sel)
                if sub_el:
                    subtitle = (await sub_el.inner_text()).strip()
                    break

            if not _looks_like_recruiter(subtitle):
                continue

            seen.add(profile_url)
            recruiters.append({
                "name": name,
                "title": subtitle or None,
                "company": company,
                "linkedin_url": profile_url,
                "source": "linkedin_people",
            })
        except Exception as e:
            logger.debug(f"Error parsing person card: {e}")
            continue

    return recruiters


async def _search_company(
    page: Page, company: str, titles: list[str], max_per_company: int
) -> list[dict]:
    # One broad keyword query per company: "<company> (recruiter OR talent OR ...)".
    title_or = " OR ".join(f'"{t}"' for t in titles)
    keywords = f"{company} ({title_or})"
    url = f"{PEOPLE_SEARCH_URL}?keywords={quote_plus(keywords)}&origin=GLOBAL_SEARCH_HEADER"

    logger.info(f"Searching recruiters at '{company}'")
    await page.goto(url, wait_until="domcontentloaded")
    await asyncio.sleep(3)

    # Nudge lazy-loaded cards into view.
    await page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
    await asyncio.sleep(1.5)

    found = await _parse_people(page, company, max_per_company)
    logger.info(f"  {company}: {len(found)} recruiter(s) found")
    return found


async def scrape_linkedin_recruiters(
    companies: list[str],
    titles: list[str] | None = None,
    max_per_company: int = 8,
    headless: bool = False,
    pace_seconds: float = 5.0,
) -> list[dict]:
    """
    Log into LinkedIn and search People for recruiters at each company.
    Returns a flat list of recruiter dicts (name, title, company, linkedin_url, source).

    headless=False lets you watch and clear any CAPTCHA / checkpoint manually.
    pace_seconds throttles between companies to reduce search rate-limiting.
    """
    titles = titles or DEFAULT_TITLES
    companies = [c for c in dict.fromkeys(c.strip() for c in companies) if c]  # de-dupe, drop blanks
    if not companies:
        logger.warning("No companies provided to recruiter scraper.")
        return []

    import os
    email = os.getenv("LINKEDIN_EMAIL", "")
    password = os.getenv("LINKEDIN_PASSWORD", "")
    if not email or not password:
        logger.error("LINKEDIN_EMAIL and LINKEDIN_PASSWORD must be set in .env")
        return []

    recruiters: list[dict] = []

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
            for i, company in enumerate(companies):
                try:
                    recruiters.extend(
                        await _search_company(page, company, titles, max_per_company)
                    )
                except Exception as e:
                    logger.warning(f"Recruiter search failed for '{company}': {e}")
                if i < len(companies) - 1:
                    await asyncio.sleep(pace_seconds)  # be gentle on People search
        except Exception as e:
            logger.error(f"LinkedIn recruiter scraper error: {e}")
        finally:
            await browser.close()

    logger.info(f"Recruiter scraping complete: {len(recruiters)} contacts found.")
    return recruiters


def scrape_linkedin_recruiters_sync(
    companies: list[str],
    titles: list[str] | None = None,
    max_per_company: int = 8,
    headless: bool = False,
    pace_seconds: float = 5.0,
) -> list[dict]:
    return asyncio.run(
        scrape_linkedin_recruiters(companies, titles, max_per_company, headless, pace_seconds)
    )
