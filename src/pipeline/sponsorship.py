"""
Known-sponsor lookup for the visa-sponsorship-history filter (M17).

Ishani is an F-1 international student; the biggest structural drag on the
Summer-2026 cycle was applications hitting the "will you require sponsorship?"
auto-reject. This module tells the scorer whether a company has a real H-1B
sponsorship history (curated from public USCIS H-1B Employer Data Hub /
MyVisaJobs data) so sponsor-friendly roles get boosted.

Soft by default — a known sponsor gets a scoring boost, but unknown companies
are NOT penalized (a small or new employer may still sponsor). A strict
`require_sponsor` filter (see job_filter.filter_jobs) is opt-in.
"""

import json
import re
from functools import lru_cache
from pathlib import Path

# src/pipeline/sponsorship.py → repo root is three levels up.
SPONSORS_PATH = Path(__file__).parent.parent.parent / "config" / "h1b_sponsors.json"

# Corporate suffixes / filler words stripped during normalization so
# "Amazon.com, Inc." and "Amazon" compare equal.
_SUFFIXES = re.compile(
    r"\b(inc|llc|corp|corporation|co|com|company|ltd|limited|plc|lp|llp|"
    r"gmbh|holdings|group|technologies|technology|labs|the|usa|us)\b"
)


def _normalize(name: str) -> str:
    """Lowercase, drop punctuation + corporate suffixes, collapse whitespace."""
    n = (name or "").lower()
    n = re.sub(r"[.,/&'\-()]", " ", n)
    n = _SUFFIXES.sub(" ", n)
    n = re.sub(r"\s+", " ", n).strip()
    return n


def _load_names(key: str) -> frozenset[str]:
    """Normalized set of company names under `key` in the sponsors JSON."""
    try:
        data = json.loads(SPONSORS_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return frozenset()
    names = data.get(key, []) if isinstance(data, dict) else (data if key == "sponsors" else [])
    out = set()
    for entry in names:
        name = entry.get("name") if isinstance(entry, dict) else entry
        norm = _normalize(name or "")
        if norm:
            out.add(norm)
    return frozenset(out)


@lru_cache(maxsize=1)
def _load_sponsors() -> frozenset[str]:
    """Normalized set of known-sponsor company names (cached)."""
    return _load_names("sponsors")


@lru_cache(maxsize=1)
def _load_itar_exclusions() -> frozenset[str]:
    """Normalized set of defense/ITAR employers that won't sponsor (cached)."""
    return _load_names("defense_itar_exclusions")


def _token_subset_match(company: str, catalog: frozenset[str]) -> bool:
    """True if `company` exactly matches, or is a token-superset of, a catalog
    name — so "Amazon Web Services" matches "Amazon", while "Metabolic Labs" is
    NOT matched by "Meta"."""
    norm = _normalize(company)
    if not norm:
        return False
    if norm in catalog:
        return True
    ctokens = set(norm.split())
    for entry in catalog:
        etokens = entry.split()
        if etokens and set(etokens) <= ctokens:
            return True
    return False


def is_defense_itar_excluded(company: str) -> bool:
    """True if `company` is a defense/aerospace or export-controlled (ITAR/EAR)
    employer that typically requires US-person status and won't sponsor an
    F-1/H-1B (curated in h1b_sponsors.json → defense_itar_exclusions)."""
    return _token_subset_match(company, _load_itar_exclusions())


def is_known_sponsor(company: str) -> bool:
    """True if `company` matches a known H-1B sponsor.

    ITAR/defense-excluded employers are never treated as sponsors, even when the
    name also token-matches the sponsors list (e.g. SpaceX, Anduril) — they
    require US-person status and won't sponsor.
    """
    if is_defense_itar_excluded(company):
        return False
    return _token_subset_match(company, _load_sponsors())


def sponsor_score(company: str) -> float:
    """1.0 if the company is a known sponsor, else 0.0."""
    return 1.0 if is_known_sponsor(company) else 0.0
