"""
Jobright detail-page enrichment.

Pulls richer metadata from the public Jobright detail page, attempts to find
the underlying employer posting URL, and detects obviously closed listings.
"""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass
from datetime import datetime
from html import unescape
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

LOGIN_URL = "https://jobright.ai/swan/auth/login/pwd"

AGGREGATOR_DOMAINS = {
    "jobright.ai",
    "linkedin.com",
    "www.linkedin.com",
    "indeed.com",
    "www.indeed.com",
    "glassdoor.com",
    "www.glassdoor.com",
    "ziprecruiter.com",
    "www.ziprecruiter.com",
    "simplyhired.com",
    "www.simplyhired.com",
    "talent.com",
    "www.talent.com",
    "jooble.org",
    "www.jooble.org",
    "monster.com",
    "www.monster.com",
    "techjobsforgood.com",
    "www.techjobsforgood.com",
}

ATS_HINTS = (
    "greenhouse.io",
    "lever.co",
    "myworkdayjobs.com",
    "workdayjobs.com",
    "workday.com",
    "icims.com",
    "successfactors.com",
    "dayforcehcm.com",
    "oraclecloud.com",
    "ashbyhq.com",
    "smartrecruiters.com",
    "ultipro.com",
)

_session: requests.Session | None = None


@dataclass
class JobrightEnrichment:
    title: str = ""
    company: str = ""
    location: str = ""
    salary_range: str = ""
    description: str = ""
    employer_url: str = ""
    company_url: str = ""
    work_model: str = ""
    employment_type: str = ""
    seniority: str = ""
    valid_through: str = ""
    recommendation_tags: list[str] | None = None
    core_skills: list[str] | None = None
    is_closed: bool = False
    closed_reason: str = ""


def is_jobright_url(url: str | None) -> bool:
    return bool(url and "jobright.ai/jobs/info/" in url)


def _get_session() -> requests.Session:
    global _session
    if _session is not None:
        return _session

    email = os.getenv("JOBRIGHT_EMAIL", "")
    password = os.getenv("JOBRIGHT_PASSWORD", "")

    sess = requests.Session()
    sess.headers.update(HEADERS)

    if email and password:
        try:
            resp = sess.post(
                LOGIN_URL,
                json={"email": email, "password": password},
                timeout=15,
            )
            resp.raise_for_status()
            logger.debug("Jobright login successful")
        except requests.RequestException as exc:
            logger.warning("Jobright login failed: %s", exc)
    else:
        logger.warning("JOBRIGHT_EMAIL/JOBRIGHT_PASSWORD not set; fetching without auth")

    _session = sess
    return _session


def enrich_jobright_url(url: str) -> JobrightEnrichment:
    sess = _get_session()
    resp = sess.get(url, timeout=25)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    next_data = _load_next_data(soup)
    job_data = (((next_data.get("props") or {}).get("pageProps") or {}).get("dataSource") or {}).get("jobResult") or {}
    company_data = (((next_data.get("props") or {}).get("pageProps") or {}).get("dataSource") or {}).get("companyResult") or {}
    schema_data = _load_job_schema(soup)

    title = str(job_data.get("jobTitle") or schema_data.get("title") or "").strip()
    company = _coalesce_company(job_data, company_data, schema_data)
    location = str(job_data.get("jobLocation") or _schema_location(schema_data) or "").strip()
    salary_range = str(job_data.get("salaryDesc") or "").strip()
    company_url = str(company_data.get("companyURL") or ((schema_data.get("hiringOrganization") or {}).get("sameAs")) or "").strip()
    employer_url = _extract_origin_url(soup) or _find_employer_url(title, company, company_url)
    valid_through = str(schema_data.get("validThrough") or "").strip()
    closed_reason = _detect_closed_reason(resp.text, soup, valid_through)

    return JobrightEnrichment(
        title=title,
        company=company,
        location=location,
        salary_range=salary_range,
        description=_build_description(job_data, schema_data, company_data),
        employer_url=employer_url,
        company_url=company_url,
        work_model=str(job_data.get("workModel") or "").strip(),
        employment_type=str(job_data.get("employmentType") or "").strip(),
        seniority=str(job_data.get("jobSeniority") or "").strip(),
        valid_through=valid_through,
        recommendation_tags=[str(tag).strip() for tag in (job_data.get("recommendationTags") or []) if str(tag).strip()],
        core_skills=[
            str(item.get("skill")).strip()
            for item in (job_data.get("jdCoreSkills") or [])
            if isinstance(item, dict) and str(item.get("skill") or "").strip()
        ],
        is_closed=bool(closed_reason),
        closed_reason=closed_reason,
    )


def _extract_origin_url(soup: BeautifulSoup) -> str:
    """Extract the 'Original Job Post' employer URL from the logged-in page."""
    anchor = soup.find("a", class_=lambda c: c and "origin" in c)
    if anchor:
        href = str(anchor.get("href") or "").strip()
        if href.startswith("http"):
            return href
    return ""


def _load_next_data(soup: BeautifulSoup) -> dict[str, Any]:
    script = soup.find("script", id="__NEXT_DATA__")
    if not script or not script.string:
        return {}
    try:
        return json.loads(script.string)
    except json.JSONDecodeError:
        logger.warning("Could not decode Jobright __NEXT_DATA__ payload")
        return {}


def _load_job_schema(soup: BeautifulSoup) -> dict[str, Any]:
    for script in soup.find_all("script", type="application/ld+json"):
        if not script.string:
            continue
        try:
            payload = json.loads(script.string)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict) and payload.get("@type") == "JobPosting":
            return payload
    return {}


def _schema_location(schema_data: dict[str, Any]) -> str:
    address = ((schema_data.get("jobLocation") or {}).get("address") or {})
    locality = str(address.get("addressLocality") or "").strip()
    region = str(address.get("addressRegion") or "").strip()
    country = str(address.get("addressCountry") or "").strip()
    parts = [part for part in (locality, region, country) if part]
    return ", ".join(parts[:2]) if parts else ""


def _coalesce_company(job_data: dict[str, Any], company_data: dict[str, Any], schema_data: dict[str, Any]) -> str:
    schema_org = schema_data.get("hiringOrganization") or {}
    return str(
        company_data.get("companyName")
        or schema_org.get("name")
        or ((schema_data.get("identifier") or {}).get("name"))
        or ""
    ).strip()


def _build_description(job_data: dict[str, Any], schema_data: dict[str, Any], company_data: dict[str, Any]) -> str:
    sections: list[str] = []

    summary = str(job_data.get("jobSummary") or "").strip()
    if summary:
        sections.append(f"Overview\n{summary}")

    responsibilities = [str(item).strip() for item in (job_data.get("coreResponsibilities") or []) if str(item).strip()]
    if responsibilities:
        sections.append("Responsibilities\n" + "\n".join(f"- {item}" for item in responsibilities))

    qualifications = job_data.get("qualifications") or {}
    must_have = [str(item).strip() for item in (qualifications.get("mustHave") or []) if str(item).strip()]
    preferred = [str(item).strip() for item in (qualifications.get("preferredHave") or []) if str(item).strip()]
    if must_have:
        sections.append("Required Qualifications\n" + "\n".join(f"- {item}" for item in must_have))
    if preferred:
        sections.append("Preferred Qualifications\n" + "\n".join(f"- {item}" for item in preferred))

    skills = [
        str(item.get("skill")).strip()
        for item in (job_data.get("jdCoreSkills") or [])
        if isinstance(item, dict) and str(item.get("skill") or "").strip()
    ]
    if skills:
        sections.append("Core Skills\n" + ", ".join(skills))

    recommendation_tags = [str(item).strip() for item in (job_data.get("recommendationTags") or []) if str(item).strip()]
    if recommendation_tags:
        sections.append("Signals\n" + ", ".join(recommendation_tags))

    company_summary = str(company_data.get("companySummary") or "").strip()
    if company_summary:
        sections.append(f"Company\n{company_summary}")

    if sections:
        return "\n\n".join(sections)

    html_description = str(schema_data.get("description") or "")
    if not html_description:
        return ""

    clean = BeautifulSoup(unescape(html_description), "html.parser").get_text("\n", strip=True)
    clean = re.sub(r"\n{3,}", "\n\n", clean)
    return clean.strip()


def _detect_closed_reason(html: str, soup: BeautifulSoup, valid_through: str) -> str:
    text = soup.get_text(" ", strip=True).lower()
    closed_markers = [
        "job expired",
        "position has been filled",
        "no longer accepting applications",
        "this job is no longer available",
        "job is closed",
        "application closed",
        "expired job",
    ]
    for marker in closed_markers:
        if marker in text:
            return marker

    if valid_through:
        try:
            expiry = datetime.fromisoformat(valid_through.replace("Z", "+00:00"))
            if expiry.date() < datetime.utcnow().date():
                return f"validThrough passed on {expiry.date().isoformat()}"
        except ValueError:
            pass

    html_lower = html.lower()
    apply_ctas = (
        "apply now",
        "apply on employer site",
        "apply-now-button-id",   # logged-in apply button id
        "apply with autofill",   # logged-in apply button text
        "index_origin__",        # "Original Job Post" link (logged-in)
    )
    if not any(cta in html_lower for cta in apply_ctas):
        return "apply CTA missing"

    return ""


def _find_employer_url(title: str, company: str, company_url: str) -> str:
    company_host = _normalize_host(company_url)
    best_url = ""
    best_score = -1

    for query in _search_queries(title, company):
        for resolved in _search_candidate_urls(query):
            score = _score_candidate_url(resolved, company_host, title, company)
            if score > best_score:
                best_score = score
                best_url = resolved
            if best_score >= 10:
                return best_url

    return best_url if best_score >= 3 else ""


def _search_queries(title: str, company: str) -> list[str]:
    queries = [
        f"\"{title}\" \"{company}\"",
        f"{title} {company} careers",
        f"{title} {company} internship",
    ]
    simple_title = re.sub(r"\s*\([^)]*\)", "", title).strip()
    if simple_title and simple_title != title:
        queries.append(f"\"{simple_title}\" \"{company}\"")
        queries.append(f"{simple_title} {company} careers")
    return queries


def _search_candidate_urls(query: str) -> list[str]:
    urls: list[str] = []
    seen: set[str] = set()
    for provider in (_duckduckgo_results, _bing_results):
        try:
            for url in provider(query):
                if url and url not in seen:
                    seen.add(url)
                    urls.append(url)
        except requests.RequestException as exc:
            logger.warning("%s search failed for %s: %s", provider.__name__, query, exc)
    return urls


def _duckduckgo_results(query: str) -> list[str]:
    resp = requests.get(
        "https://duckduckgo.com/html/",
        params={"q": query},
        headers=HEADERS,
        timeout=6,
    )
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    urls = []
    for anchor in soup.select("a.result__a"):
        raw_href = (anchor.get("href") or "").strip()
        resolved = _unwrap_duckduckgo_link(raw_href)
        if resolved and resolved.startswith("http"):
            urls.append(resolved)
    return urls


def _bing_results(query: str) -> list[str]:
    resp = requests.get(
        "https://www.bing.com/search",
        params={"q": query},
        headers=HEADERS,
        timeout=6,
    )
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    urls = []
    for anchor in soup.select("li.b_algo h2 a"):
        href = (anchor.get("href") or "").strip()
        resolved = _unwrap_bing_link(href)
        if resolved and resolved.startswith("http"):
            urls.append(resolved)
    return urls


def _unwrap_duckduckgo_link(href: str) -> str:
    if href.startswith("//duckduckgo.com/l/?"):
        href = "https:" + href
    parsed = urlparse(href)
    if "duckduckgo.com" in parsed.netloc:
        uddg = parse_qs(parsed.query).get("uddg")
        if uddg:
            return unquote(uddg[0])
    return href


def _unwrap_bing_link(href: str) -> str:
    parsed = urlparse(href)
    if "bing.com" not in parsed.netloc:
        return href
    target = parse_qs(parsed.query).get("u")
    if target:
        value = target[0]
        if value.startswith("a1"):
            try:
                value = bytes.fromhex(value[2:]).decode("utf-8", errors="ignore")
            except ValueError:
                pass
        if value.startswith("http"):
            return value
    return href


def _normalize_host(url: str) -> str:
    if not url:
        return ""
    parsed = urlparse(url if "://" in url else f"https://{url}")
    host = parsed.netloc.lower()
    return host[4:] if host.startswith("www.") else host


def _score_candidate_url(url: str, company_host: str, title: str, company: str) -> int:
    host = _normalize_host(url)
    if not host:
        return -10

    score = 0
    if host in AGGREGATOR_DOMAINS:
        score -= 8
    if company_host and (host == company_host or host.endswith(f".{company_host}")):
        score += 6
    if any(hint in host for hint in ATS_HINTS):
        score += 4
    if "/jobs/" in url or "/careers/" in url or "/job/" in url:
        score += 2
    normalized = re.sub(r"[^a-z0-9]+", " ", url.lower())
    for token in _meaningful_tokens(title):
        if token in normalized:
            score += 1
    for token in _meaningful_tokens(company):
        if token in normalized:
            score += 1
    if "linkedin.com" in host:
        score -= 3
    return score


def _meaningful_tokens(text: str) -> list[str]:
    tokens = re.findall(r"[a-z0-9]{3,}", text.lower())
    stop = {"intern", "internship", "research", "scientist", "engineer", "summer", "start"}
    return [token for token in tokens if token not in stop][:6]
