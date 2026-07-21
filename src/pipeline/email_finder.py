"""
Best-effort recruiter email discovery via a free-tier provider waterfall.

Given a person (name + optional company domain + optional LinkedIn URL), resolve
the most likely email address. The waterfall, highest-confidence first:

  1. Prospeo by LinkedIn URL   — login-free; turns a /in/ profile into an email
  2. SMTP / Reacher verify     — confirm pattern candidates against the mail server
  3. Finder APIs (name+domain) — Hunter → Prospeo → Tomba (free tiers)
  4. Pattern inference         — Hunter Domain Search reveals the company pattern
  5. Ranked guesses            — unrejected candidate patterns, best first

Every provider is a no-op unless its API key is set, so with no keys the module
degrades to the original SMTP-probe + pattern-guess behaviour.

Free tiers (set the matching env var to enable):
  HUNTER_API_KEY    — Hunter.io,  ~50 credits/month
  PROSPEO_API_KEY   — Prospeo.io, 100 free credits (LinkedIn-URL + name finder)
  TOMBA_API_KEY + TOMBA_SECRET — Tomba.io, 25 searches/month
  REACHER_URL [+ REACHER_API_KEY] — self-hosted/hosted Reacher verifier (Gmail/MS-aware)

Reality check: many providers/mail servers (Google, Microsoft) run catch-all or
reject SMTP probes, so verification is often inconclusive. In that case we return
the unrejected candidates ranked by likelihood. We return [] only when there is
nothing to go on (no domain and no LinkedIn URL) or every candidate is explicitly
rejected and no provider finds anything.
"""

import logging
import os
import re
import smtplib

import requests

logger = logging.getLogger(__name__)

PROBE_FROM = "verify@example.com"   # envelope sender for the probe; never receives mail
HUNTER_URL = "https://api.hunter.io/v2/email-finder"
HUNTER_DOMAIN_URL = "https://api.hunter.io/v2/domain-search"
PROSPEO_ENRICH_URL = "https://api.prospeo.io/enrich-person"
PROSPEO_FINDER_URL = "https://api.prospeo.io/email-finder"
TOMBA_FINDER_URL = "https://api.tomba.io/v1/email-finder/{domain}"

_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")


def _extract_email(data, domain: str | None = None) -> str | None:
    """Recursively pull the first email out of a provider's JSON response. When a
    domain is given, prefer a match for it (providers sometimes echo support
    addresses elsewhere in the payload)."""
    found: list[str] = []

    def walk(x):
        if isinstance(x, str):
            found.extend(_EMAIL_RE.findall(x))
        elif isinstance(x, dict):
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)

    walk(data)
    if domain:
        d = domain.lower()
        for e in found:
            if e.lower().endswith("@" + d):
                return e
    return found[0] if found else None


def _candidate_patterns(first: str, last: str, domain: str) -> list[str]:
    """The 6 most common corporate address patterns, ranked by prevalence."""
    f = first.strip().lower()
    last_l = last.strip().lower()
    d = domain.strip().lower().lstrip("@")
    if not f or not last_l or not d:
        return []
    fi = f[0]
    patterns = [
        f"{f}.{last_l}@{d}",   # first.last  (most common)
        f"{f}{last_l}@{d}",    # firstlast
        f"{fi}{last_l}@{d}",   # flast
        f"{f}@{d}",            # first
        f"{fi}.{last_l}@{d}",  # f.last
        f"{last_l}{f}@{d}",    # lastfirst
    ]
    # de-dupe while preserving order (e.g. single-letter names can collide)
    seen: set[str] = set()
    return [p for p in patterns if not (p in seen or seen.add(p))]


def _mx_host(domain: str) -> str | None:
    """Lowest-priority MX host for the domain, or None if unresolvable."""
    try:
        import dns.resolver
        answers = dns.resolver.resolve(domain, "MX")
        best = min(answers, key=lambda r: r.preference)
        return str(best.exchange).rstrip(".")
    except Exception as e:
        logger.info(f"MX lookup failed for {domain}: {e}")
        return None


def _smtp_probe(email: str, mx_host: str) -> bool | None:
    """Probe one address via SMTP RCPT TO. True=accepted, False=rejected,
    None=inconclusive (couldn't connect, greylisted, port blocked, etc.)."""
    try:
        with smtplib.SMTP(mx_host, 25, timeout=10) as smtp:
            smtp.helo("example.com")
            smtp.mail(PROBE_FROM)
            code, _ = smtp.rcpt(email)
            if code in (250, 251):
                return True
            if code in (550, 551, 553):
                return False
            return None
    except Exception as e:
        logger.info(f"SMTP probe inconclusive for {email}: {e}")
        return None


def _reacher_verify(email: str) -> bool | None:
    """Verify via a Reacher / check-if-email-exists backend (Gmail/Outlook-aware,
    catch-all detection). True=safe, False=invalid, None=risky/unknown/unset.
    No-op unless REACHER_URL is set."""
    base = os.getenv("REACHER_URL")
    if not base:
        return None
    headers = {"Content-Type": "application/json"}
    key = os.getenv("REACHER_API_KEY")
    if key:
        headers["Authorization"] = key
    try:
        resp = requests.post(
            f"{base.rstrip('/')}/v0/check_email",
            json={"to_email": email},
            headers=headers,
            timeout=30,
        )
        resp.raise_for_status()
        reachable = (resp.json() or {}).get("is_reachable")
        if reachable == "safe":
            return True
        if reachable == "invalid":
            return False
        return None  # risky / unknown
    except Exception as e:
        logger.info(f"Reacher verify inconclusive for {email}: {e}")
        return None


def _verify_address(email: str, mx_host: str | None) -> bool | None:
    """Confirm an address: prefer Reacher when configured (handles Gmail/MS where
    raw SMTP fails), else fall back to the SMTP RCPT probe."""
    if os.getenv("REACHER_URL"):
        return _reacher_verify(email)
    if mx_host:
        return _smtp_probe(email, mx_host)
    return None


def _hunter_lookup(first: str, last: str, domain: str) -> str | None:
    """Hunter.io email-finder. Returns an address or None. No-op without
    HUNTER_API_KEY."""
    key = os.getenv("HUNTER_API_KEY")
    if not key:
        return None
    try:
        resp = requests.get(
            HUNTER_URL,
            params={"domain": domain, "first_name": first, "last_name": last, "api_key": key},
            timeout=15,
        )
        resp.raise_for_status()
        return ((resp.json() or {}).get("data") or {}).get("email")
    except Exception as e:
        logger.warning(f"Hunter.io lookup failed for {first} {last} @ {domain}: {e}")
        return None


def _prospeo_by_linkedin(linkedin_url: str) -> str | None:
    """Prospeo person-enrichment by LinkedIn profile URL → work email. Login-free:
    resolves the email without touching LinkedIn auth. No-op without PROSPEO_API_KEY."""
    key = os.getenv("PROSPEO_API_KEY")
    if not key or not linkedin_url:
        return None
    try:
        resp = requests.post(
            PROSPEO_ENRICH_URL,
            json={"url": linkedin_url},
            headers={"Content-Type": "application/json", "X-KEY": key},
            timeout=20,
        )
        resp.raise_for_status()
        return _extract_email(resp.json())
    except Exception as e:
        logger.warning(f"Prospeo LinkedIn enrich failed for {linkedin_url}: {e}")
        return None


def _prospeo_finder(first: str, last: str, domain: str) -> str | None:
    """Prospeo email-finder by name + company domain. No-op without PROSPEO_API_KEY."""
    key = os.getenv("PROSPEO_API_KEY")
    if not key:
        return None
    try:
        resp = requests.post(
            PROSPEO_FINDER_URL,
            json={"first_name": first, "last_name": last, "company": domain},
            headers={"Content-Type": "application/json", "X-KEY": key},
            timeout=20,
        )
        resp.raise_for_status()
        return _extract_email(resp.json(), domain)
    except Exception as e:
        logger.warning(f"Prospeo finder failed for {first} {last} @ {domain}: {e}")
        return None


def _tomba_finder(first: str, last: str, domain: str) -> str | None:
    """Tomba.io email-finder by name + domain. No-op without TOMBA_API_KEY +
    TOMBA_SECRET."""
    key = os.getenv("TOMBA_API_KEY")
    secret = os.getenv("TOMBA_SECRET")
    if not key or not secret:
        return None
    try:
        resp = requests.get(
            TOMBA_FINDER_URL.format(domain=domain),
            params={"first_name": first, "last_name": last},
            headers={"X-Tomba-Key": key, "X-Tomba-Secret": secret},
            timeout=20,
        )
        resp.raise_for_status()
        return _extract_email(resp.json(), domain)
    except Exception as e:
        logger.warning(f"Tomba finder failed for {first} {last} @ {domain}: {e}")
        return None


def _hunter_domain_pattern(domain: str) -> str | None:
    """Hunter.io Domain Search returns the company's dominant address pattern
    (e.g. '{first}.{last}'). Returns the pattern template or None. No-op without
    HUNTER_API_KEY. Cheaper than per-person guessing: one lookup unlocks every
    contact at the company."""
    key = os.getenv("HUNTER_API_KEY")
    if not key:
        return None
    try:
        resp = requests.get(
            HUNTER_DOMAIN_URL,
            params={"domain": domain, "api_key": key},
            timeout=15,
        )
        resp.raise_for_status()
        return ((resp.json() or {}).get("data") or {}).get("pattern") or None
    except Exception as e:
        logger.warning(f"Hunter.io domain search failed for {domain}: {e}")
        return None


def _apply_pattern(pattern: str, first: str, last: str, domain: str) -> str | None:
    """Build an address from a Hunter pattern template. Hunter uses {first},
    {last}, {f} (first initial), {l} (last initial), optionally separated by
    '.', '_' or nothing."""
    f = first.strip().lower()
    last_l = last.strip().lower()
    d = domain.strip().lower().lstrip("@")
    if not f or not last_l or not d or not pattern:
        return None
    local = (
        pattern.replace("{first}", f)
        .replace("{last}", last_l)
        .replace("{f}", f[0])
        .replace("{l}", last_l[0])
    )
    if "{" in local or not local:
        return None  # unrecognised token — don't emit a malformed address
    return f"{local}@{d}"


def guess_emails(
    first: str,
    last: str,
    domain: str = "",
    probe: bool = True,
    linkedin_url: str | None = None,
) -> list[str]:
    """Return likely email addresses for a person, best first.

    A LinkedIn URL alone is enough (Prospeo resolves it without a domain). With a
    domain, verified addresses lead, then finder APIs, then pattern inference, then
    ranked guesses. Returns [] only when there's nothing to go on or every
    candidate is explicitly rejected and no provider finds anything.
    """
    clean_domain = domain.strip().lower().lstrip("@")

    # 1. LinkedIn URL → email (login-free, no domain required). Highest value.
    if linkedin_url:
        em = _prospeo_by_linkedin(linkedin_url)
        if em:
            return [em]

    candidates = _candidate_patterns(first, last, clean_domain)
    if not candidates:
        return []  # no domain to pattern/verify against, and URL lookup found nothing

    # 2. Verify candidates against the mail server (Reacher if configured, else SMTP).
    verified: list[str] = []
    rejected: set[str] = set()
    if probe:
        mx = _mx_host(clean_domain) if not os.getenv("REACHER_URL") else None
        if mx or os.getenv("REACHER_URL"):
            for c in candidates:
                res = _verify_address(c, mx)
                if res is True:
                    verified.append(c)
                elif res is False:
                    rejected.add(c)
    if verified:
        return verified

    # 3. Finder APIs by name + domain (free tiers). First confirmed hit wins.
    for finder in (_hunter_lookup, _prospeo_finder, _tomba_finder):
        em = finder(first, last, clean_domain)
        if em and em not in rejected:
            return [em]

    # 4. Learn the company's dominant pattern once and construct this address.
    pattern = _hunter_domain_pattern(clean_domain)
    if pattern:
        constructed = _apply_pattern(pattern, first, last, clean_domain)
        if constructed and constructed not in rejected:
            ranked = [c for c in candidates if c not in rejected and c != constructed]
            return [constructed, *ranked]

    # 5. Inconclusive → return what we couldn't disprove, ranked.
    return [c for c in candidates if c not in rejected]
