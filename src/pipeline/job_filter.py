"""
Scores and filters job listings against Ishani's profile and target criteria.
No LLM needed here — pure keyword/heuristic scoring for Phase 1.
"""

import logging

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

EXCLUDE_KEYWORDS = [
    "no sponsorship", "no visa", "citizens only", "us citizen",
    "security clearance", "clearance required", "secret clearance",
    "top secret", "must be authorized",
]

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

    if _is_excluded(text) or is_phd_only(text):
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

    # Sponsorship-friendly signals boost (0–0.10)
    if _matches_any(text, SPONSORSHIP_POSITIVE):
        score += 0.10

    # Recency bonus (0–0.15) — prefer recently scraped
    score += 0.15

    # Soft seniority penalty — sinks over-senior roles below new-grad-appropriate
    # ones without discarding them (a mislabeled "II" role still survives).
    if _is_too_senior(job, text):
        score *= SENIORITY_PENALTY

    return round(min(score, 1.0), 3)


def filter_jobs(jobs: list[dict], min_score: float = 0.0, skip_phd: bool = True) -> list[dict]:
    """
    Score all jobs, attach score, filter below threshold, sort by score desc.
    min_score=0.0 keeps all listings (score still computed for ranking).

    When skip_phd is True (default), jobs that require a PhD (and don't accept a
    Master's) are tagged with status "skipped" so they enter the DB out of the
    active pipeline rather than as "new". "skipped" matches tracker.STATUS_SKIPPED.
    """
    scored = []
    n_phd = 0
    for job in jobs:
        text = _combined_text(job)
        s = score_job(job)
        if s >= min_score:
            job["score"] = s
            if skip_phd and is_phd_only(text):
                job["status"] = "skipped"
                n_phd += 1
            scored.append(job)

    scored.sort(key=lambda j: j["score"], reverse=True)
    logger.info(
        f"Filtered {len(scored)} / {len(jobs)} jobs above score {min_score}"
        + (f"; {n_phd} PhD-only tagged skipped" if n_phd else "")
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
    return any(kw in text for kw in EXCLUDE_KEYWORDS)


def is_phd_only(text: str) -> bool:
    """True if the role requires a PhD with no indication a Master's is accepted.
    `text` should already be lowercased (e.g. from `_combined_text`)."""
    if any(s in text for s in MASTERS_OK):
        return False
    return any(s in text for s in PHD_REQUIRED)
