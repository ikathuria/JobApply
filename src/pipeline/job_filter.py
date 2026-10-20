"""
Scores and filters job listings against Ishani's profile and target criteria.
No LLM needed here — pure keyword/heuristic scoring for Phase 1.
"""

import logging
import re

from pipeline.sponsorship import is_known_sponsor

logger = logging.getLogger(__name__)

# Keywords strongly matching Ishani's profile
STRONG_MATCH_KEYWORDS = [
    "llm", "large language model", "generative ai", "gen ai", "rag",
    "retrieval augmented", "langchain", "huggingface", "hugging face",
    "transformer", "fine-tun", "prompt engineering", "multi-agent",
    "agentic", "openai", "llama", "gemini", "bedrock",
]

GOOD_MATCH_KEYWORDS = [
    "machine learning", "deep learning", "natural language processing", "nlp",
    "computer vision", "pytorch", "tensorflow", "python", "aws",
    "artificial intelligence", "ai research", "ml engineer", "mlops",
    "neural network", "model training", "data science",
]

ROLE_KEYWORDS = [
    # internships / co-ops (still in scope for CPT during the school year)
    "intern", "internship", "co-op", "coop",
    # full-time new-grad / entry-level (primary target since 2026-07-19)
    "new grad", "new graduate", "newgrad", "recent graduate",
    "entry level", "entry-level", "early career", "university graduate",
    "university grad", "campus", "graduate program", "grad program",
    "associate engineer", "associate software", "associate machine",
    "full time", "full-time",
]

# Jobs from these curated feeds are the right role type by construction
# (intern-list = internships, newgrad-jobs = full-time new-grad), so they pass
# the role gate even when the JD text omits an explicit keyword.
NEWGRAD_FEED_SOURCES = {"newgrad-jobs.com", "intern-list.com"}

# Title signals that a role is too senior for a new-grad / intern search. Applied
# as a soft penalty (not a hard 0) — see SENIORITY_PENALTY — and skipped when the
# title itself clearly says intern / new-grad / entry / associate (JUNIOR_TITLE).
SENIORITY_TITLE_KEYWORDS = [
    "senior", "sr.", "sr ", "staff", "principal", "lead", "director",
    "manager", "head of", "vp ", "vice president", "architect",
]
JUNIOR_TITLE_KEYWORDS = [
    "intern", "new grad", "new graduate", "entry level", "entry-level",
    "graduate", "associate", "co-op", "coop", "campus", "junior",
]
# Explicit multi-year experience requirements — a new-grad role won't ask for these.
EXPERIENCE_REQUIRED = [
    "5+ years", "6+ years", "7+ years", "8+ years", "9+ years", "10+ years",
    "5 + years", "minimum of 5 years", "minimum 5 years", "at least 5 years",
]
SENIORITY_PENALTY = 0.25  # multiply the score — sinks senior roles without discarding

# Roles an F-1/OPT candidate can't take: clearance, citizenship / US-person
# (ITAR), or an explicit "no sponsorship now or in the future". Regexes with word
# boundaries ("itar" must not hit "military"). Plain "must be authorized to work"
# is deliberately absent — OPT *is* work authorization. Jobright's own tags
# ("No H1B", "Citizen Only") ride along in enriched descriptions (Signals).
EXCLUDE_PATTERNS = [
    # clearance
    r"security clearance", r"clearance (is )?required", r"secret clearance",
    r"top secret", r"\bts/sci\b", r"polygraph", r"public trust",
    # citizenship / US person
    r"\bu\.?s\.? citizens?(hip)?\b(?! status)", r"citizens? only",
    r"citizenship (is )?required", r"\bu\.?s\.? persons?\b", r"\bitar\b",
    # sponsorship denied
    r"\bno (visa )?sponsorship\b", r"\bno visa\b", r"\bno h-?1b\b",
    r"\b(unable to|not able to|cannot|can not|will not|won'?t|does not|doesn'?t|do not|don'?t)"
    r" (provide |offer |support )?(any )?(visa |employment visa |immigration )?sponsor",
    r"not (offer|provide)(ing)? (visa )?sponsorship",
    r"sponsorship (is )?not (offered|available|provided)",
    r"without (the need for |need for |requiring )?(visa |employer )?sponsorship",
    r"authorized to work permanently",
    r"work in the (united states|u\.?s\.?) without restriction",
]
_EXCLUDE_RE = re.compile("|".join(f"(?:{p})" for p in EXCLUDE_PATTERNS), re.I)

# Roles that start before OPT does (May 2027) — no CPT, so nothing earlier is
# workable: new-grad programs for the class of 2026 or earlier, any 2026 term,
# Winter/Spring 2027 terms, and explicit Jan–Apr 2027 start dates. Summer/Fall
# 2027 and undated roles pass.
TIMING_PATTERNS = [
    r"\b(new|recent|college|university|campus)[ -]grad\w*\W{1,3}(class of )?(20)?2[0-6]\b",
    r"\b20(2[0-6])\b\W{1,3}(new|recent|college|university|campus)[ -]grad",
    r"\bclass of 20(2[0-6])\b",
    r"\b(summer|fall|autumn|winter|spring)\W{0,2}(20)?2[0-6]\b",
    r"\b(winter|spring)\W{0,2}(20)?27\b",
    r"\bstart(ing|s)?( date)?\W{1,3}(in |on )?(jan|feb|mar|apr)[a-z]*\.? (\d{1,2},? )?2027\b",
]
_TIMING_RE = re.compile("|".join(f"(?:{p})" for p in TIMING_PATTERNS), re.I)

# Signals that a role REQUIRES a doctorate. Used only when there's no sign a
# Master's is accepted (see MASTERS_OK) — so "MS or PhD" roles are kept.
PHD_REQUIRED = [
    "phd required", "ph.d. required", "ph.d required", "phd is required",
    "must have a phd", "must be a phd", "must hold a phd", "requires a phd",
    "phd candidate", "ph.d. candidate", "doctoral candidate", "doctoral student",
    "phd student", "ph.d. student", "pursuing a phd", "pursuing a ph.d",
    "enrolled in a phd", "enrolled in a ph.d", "phd in ", "ph.d. in ",
    "doctoral degree", "doctorate",
]

# If any of these appear, a Master's is welcome → never treat as PhD-only.
MASTERS_OK = [
    "master", "m.s.", "msc", "ms or phd", "ms/phd", "bs/ms", "m.tech", "mtech",
]

SPONSORSHIP_POSITIVE = [
    "sponsor", "opt", "cpt", "f-1", "f1 visa", "visa", "international students welcome",
]


def score_job(job: dict) -> float:
    """
    Returns a score 0.0–1.0 for a job listing.
    Considers: role type (new-grad / internship / co-op), AI/ML keyword matches,
    recency, sponsorship signals, and a soft penalty for over-senior roles.
    """
    text = _combined_text(job)

    if _is_excluded(text) or is_phd_only(text) or timing_blocker(text):
        return 0.0

    # Role gate — must be a new-grad / internship / co-op role (or come from one
    # of our curated new-grad/intern feeds). Non-matching roles score 0.0.
    if not _role_ok(job, text):
        return 0.0

    score = 0.0

    # Strong keyword matches (0–0.45)
    strong_hits = sum(1 for kw in STRONG_MATCH_KEYWORDS if kw in text)
    score += min(strong_hits / 3, 1.0) * 0.45

    # Good keyword matches (0–0.30)
    good_hits = sum(1 for kw in GOOD_MATCH_KEYWORDS if kw in text)
    score += min(good_hits / 4, 1.0) * 0.30

    # Sponsorship boost (0–0.10) — a known H-1B sponsor (company history) OR an
    # explicit visa-friendly signal in the JD. History matters more than the JD
    # rarely mentioning visas, so either lights the boost.
    if is_known_sponsor(job.get("company", "")) or _matches_any(text, SPONSORSHIP_POSITIVE):
        score += 0.10

    # Recency bonus (0–0.15) — prefer recently scraped
    score += 0.15

    # Soft seniority penalty — sinks over-senior roles below new-grad-appropriate
    # ones without discarding them (a mislabeled "II" role still survives).
    if _is_too_senior(job, text):
        score *= SENIORITY_PENALTY

    return round(min(score, 1.0), 3)


def filter_jobs(
    jobs: list[dict],
    min_score: float = 0.0,
    skip_phd: bool = True,
    require_sponsor: bool = False,
) -> list[dict]:
    """
    Score all jobs, attach score, filter below threshold, sort by score desc.
    min_score=0.0 keeps all listings (score still computed for ranking).

    When skip_phd is True (default), jobs that require a PhD (and don't accept a
    Master's) are tagged with status "skipped" so they enter the DB out of the
    active pipeline rather than as "new". "skipped" matches tracker.STATUS_SKIPPED.

    When require_sponsor is True (opt-in), jobs whose company is NOT a known H-1B
    sponsor are also tagged "skipped". Off by default — the sponsorship signal is
    a soft scoring boost, since an unknown company may still sponsor.
    """
    scored = []
    n_phd = 0
    n_blocked = 0
    n_nonsponsor = 0
    for job in jobs:
        text = _combined_text(job)
        s = score_job(job)
        if s >= min_score:
            job["score"] = s
            if skip_phd and is_phd_only(text):
                job["status"] = "skipped"
                n_phd += 1
            elif _is_excluded(text) or timing_blocker(text):
                # score 0 alone still lands in "new" when min_score is 0
                job["status"] = "skipped"
                n_blocked += 1
            elif require_sponsor and not is_known_sponsor(job.get("company", "")):
                job["status"] = "skipped"
                n_nonsponsor += 1
            scored.append(job)

    scored.sort(key=lambda j: j["score"], reverse=True)
    logger.info(
        f"Filtered {len(scored)} / {len(jobs)} jobs above score {min_score}"
        + (f"; {n_phd} PhD-only tagged skipped" if n_phd else "")
        + (f"; {n_blocked} work-auth/start-date blocked → skipped" if n_blocked else "")
        + (f"; {n_nonsponsor} non-sponsor tagged skipped" if n_nonsponsor else "")
    )
    return scored


def deduplicate(jobs: list[dict]) -> list[dict]:
    """Remove duplicate listings by URL."""
    seen = set()
    unique = []
    for job in jobs:
        url = job.get("url", "")
        if url and url not in seen:
            seen.add(url)
            unique.append(job)
    return unique


# ── helpers ──────────────────────────────────────────────────────────────────

def _combined_text(job: dict) -> str:
    parts = [
        job.get("title", ""),
        job.get("company", ""),
        job.get("description", ""),
        job.get("location", ""),
    ]
    return " ".join(parts).lower()


def _matches_any(text: str, keywords: list[str]) -> bool:
    return any(kw in text for kw in keywords)


def _role_ok(job: dict, text: str) -> bool:
    """True if the job is a new-grad / internship / co-op role we want to keep.

    Passes if a role keyword appears in the combined text or title, if the job
    came from one of our curated new-grad/intern feeds (right role type by
    construction), or if the scraper's role-type/season field says so.
    """
    if _matches_any(text, ROLE_KEYWORDS):
        return True
    if _matches_any((job.get("title", "") or "").lower(), ROLE_KEYWORDS):
        return True
    if (job.get("source", "") or "").lower() in NEWGRAD_FEED_SOURCES:
        return True
    return _matches_any((job.get("season", "") or "").lower(), ROLE_KEYWORDS)


def _is_too_senior(job: dict, text: str) -> bool:
    """True if the role reads as too senior for a new-grad / intern search.
    Title-based (with a junior-title override so genuine intern/new-grad roles
    that mention a senior-ish word aren't penalized) plus explicit multi-year
    experience requirements in the text."""
    title = (job.get("title", "") or "").lower()
    if _matches_any(title, JUNIOR_TITLE_KEYWORDS):
        return False
    if _matches_any(title, SENIORITY_TITLE_KEYWORDS):
        return True
    return _matches_any(text, EXPERIENCE_REQUIRED)


def _is_excluded(text: str) -> bool:
    return bool(_EXCLUDE_RE.search(text))


def timing_blocker(text: str) -> str | None:
    """The phrase showing a role starts before OPT (May 2027), or None."""
    m = _TIMING_RE.search(text or "")
    return m.group(0) if m else None


def work_auth_blocker(text: str) -> str | None:
    """The phrase that rules a job out for an F-1/OPT candidate (clearance,
    citizenship, or no sponsorship), or None. Used to re-check a job once its
    full JD arrives — scrape-time text is often only a short snippet."""
    m = _EXCLUDE_RE.search(text or "")
    return m.group(0) if m else None


def is_phd_only(text: str) -> bool:
    """True if the role requires a PhD with no indication a Master's is accepted.
    `text` should already be lowercased (e.g. from `_combined_text`)."""
    if any(s in text for s in MASTERS_OK):
        return False
    return any(s in text for s in PHD_REQUIRED)
