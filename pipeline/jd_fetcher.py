"""
Fetches the full job description text from a job listing URL.
Handles LinkedIn job pages, intern-list.com, and generic HTML fallback.
"""

import logging
import re
import time

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

# CSS selectors tried in order per domain
SELECTORS = {
    "linkedin.com": [
        ".jobs-description__content",
        ".jobs-box__html-content",
        "div[class*='description']",
    ],
    "intern-list.com": [
        ".job-description",
        "article",
        "main",
        "div[class*='description']",
        "div[class*='content']",
    ],
    "greenhouse.io": ["#content", ".job-post"],
    "lever.co": [".posting-description", ".content"],
    "myworkdayjobs.com": ["[data-automation-id='jobPostingDescription']"],
    "workday.com": ["[data-automation-id='jobPostingDescription']"],
    "icims.com": ["#jobDescriptionText", ".jd-info"],
}

FALLBACK_SELECTORS = ["article", "main", "[class*='description']", "[class*='job-detail']", "body"]


def fetch_jd(url: str, retries: int = 2) -> str:
    """
    Fetch and return cleaned job description text from a URL.
    Returns empty string on failure.
    """
    for attempt in range(retries + 1):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=20)
            resp.raise_for_status()
            text = _extract_text(url, resp.text)
            if text:
                return text
        except requests.RequestException as e:
            logger.warning(f"JD fetch attempt {attempt + 1} failed for {url}: {e}")
            if attempt < retries:
                time.sleep(2)

    logger.error(f"Could not fetch JD from: {url}")
    return ""


def _extract_text(url: str, html: str) -> str:
    soup = BeautifulSoup(html, "lxml")

    # Remove noise elements
    for tag in soup(["script", "style", "nav", "header", "footer", "aside"]):
        tag.decompose()

    # Pick selectors based on domain
    domain = _domain(url)
    selectors = SELECTORS.get(domain, []) + FALLBACK_SELECTORS

    for selector in selectors:
        el = soup.select_one(selector)
        if el:
            text = el.get_text(separator="\n", strip=True)
            text = _clean(text)
            if len(text) > 200:  # meaningful content threshold
                return text

    return ""


def _domain(url: str) -> str:
    for known in SELECTORS:
        if known in url:
            return known
    return ""


def _clean(text: str) -> str:
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r" {2,}", " ", text)
    return text.strip()
