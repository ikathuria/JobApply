"""
Best-effort recruiter email discovery.

Given a name + company domain, generate the most common address patterns and try
to verify them with an SMTP RCPT probe (no email is ever sent). If nothing is
confirmed and HUNTER_API_KEY is set, fall back to Hunter.io's email-finder.

Reality check: many mail providers (Google, Microsoft) reject RCPT probing or run
catch-all domains, and lots of networks block outbound port 25 — so verification
is frequently inconclusive. In that case we return the unrejected candidates
ranked by likelihood so the UI still has something to work with. Only when every
candidate is *explicitly* rejected (and Hunter finds nothing) do we return [].
"""

import logging
import os
import smtplib

import requests

logger = logging.getLogger(__name__)

PROBE_FROM = "verify@example.com"   # envelope sender for the probe; never receives mail
HUNTER_URL = "https://api.hunter.io/v2/email-finder"


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


def _hunter_lookup(first: str, last: str, domain: str) -> str | None:
    """Hunter.io email-finder fallback. Returns an address or None. No-op without
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


def guess_emails(first: str, last: str, domain: str, probe: bool = True) -> list[str]:
    """Return likely email addresses for a person at a company domain, best first.

    Verified addresses (SMTP-accepted) are returned first. If none verify, falls
    back to Hunter.io, then to the unrejected candidate patterns. Returns [] only
    when every candidate is explicitly rejected and Hunter finds nothing.
    """
    candidates = _candidate_patterns(first, last, domain)
    if not candidates:
        return []

    verified: list[str] = []
    rejected: set[str] = set()

    if probe:
        mx = _mx_host(domain.strip().lower().lstrip("@"))
        if mx:
            for c in candidates:
                res = _smtp_probe(c, mx)
                if res is True:
                    verified.append(c)
                elif res is False:
                    rejected.add(c)

    if verified:
        return verified

    hunted = _hunter_lookup(first, last, domain.strip().lower().lstrip("@"))
    if hunted:
        return [hunted]

    # Inconclusive probe → return what we couldn't disprove, ranked.
    return [c for c in candidates if c not in rejected]
