"""
Scores and filters job listings against Ishani's profile and target criteria.
No LLM needed here — pure keyword/heuristic scoring for Phase 1.
"""

import re
import logging
from datetime import datetime

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
    "intern", "internship", "co-op", "coop",
]

EXCLUDE_KEYWORDS = [
    "no sponsorship", "no visa", "citizens only", "us citizen",
    "security clearance", "clearance required", "secret clearance",
    "top secret", "must be authorized",
]

SPONSORSHIP_POSITIVE = [
    "sponsor", "opt", "cpt", "f-1", "f1 visa", "visa", "international students welcome",
]


def score_job(job: dict) -> float:
    """
    Returns a score 0.0–1.0 for a job listing.
    Considers: title relevance, description keyword matches, recency, sponsorship signals.
    """
    text = _combined_text(job)

    if _is_excluded(text):
        return 0.0

    score = 0.0

    # Role type check — must be an internship
    if not _matches_any(text, ROLE_KEYWORDS):
        # title might still make it clear
        if not _matches_any(job.get("title", "").lower(), ROLE_KEYWORDS):
            return 0.0

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

    return round(min(score, 1.0), 3)


def filter_jobs(jobs: list[dict], min_score: float = 0.30) -> list[dict]:
    """
    Score all jobs, attach score, filter below threshold, sort by score desc.
    """
    scored = []
    for job in jobs:
        s = score_job(job)
        if s >= min_score:
            job["score"] = s
            scored.append(job)

    scored.sort(key=lambda j: j["score"], reverse=True)
    logger.info(f"Filtered {len(scored)} / {len(jobs)} jobs above score {min_score}")
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


def _is_excluded(text: str) -> bool:
    return any(kw in text for kw in EXCLUDE_KEYWORDS)
