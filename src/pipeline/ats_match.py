"""
ATS keyword-match score (M21).

Applicant-tracking systems keyword-filter resumes before a human sees them. This
computes, for a given job, which skill/tool keywords the job description asks for
and which of those actually appear in the candidate's materials — surfacing the
gaps to close before applying. Deterministic (a curated vocabulary + word-boundary
matching), so it's instant, free, and testable.

The "resume" side is built from ``config/profile.json`` (skills, experience,
projects, summary) — i.e. what the candidate can credibly claim anywhere in their
materials — rather than a single tailored PDF.
"""

import json
import re
from pathlib import Path

PROFILE_PATH = Path("config/profile.json")

# Canonical keyword → the regex alternatives that count as a hit for it. Kept
# lowercase; matching is case-insensitive and word-boundary aware.
VOCAB: dict[str, list[str]] = {
    "python": ["python"],
    "java": ["java"],
    "c++": [r"c\+\+"],
    "sql": ["sql"],
    "javascript": ["javascript", "js"],
    "typescript": ["typescript"],
    "scala": ["scala"],
    "go": ["golang"],
    "r": [],  # too ambiguous as a single letter — matched only via phrases below
    "pytorch": ["pytorch", "torch"],
    "tensorflow": ["tensorflow", "tf"],
    "keras": ["keras"],
    "scikit-learn": ["scikit-learn", "sklearn", "scikit learn"],
    "pandas": ["pandas"],
    "numpy": ["numpy"],
    "spark": ["spark", "pyspark"],
    "hadoop": ["hadoop"],
    "hugging face": ["hugging face", "huggingface", "transformers library"],
    "langchain": ["langchain"],
    "machine learning": ["machine learning", r"\bml\b"],
    "deep learning": ["deep learning"],
    "neural networks": ["neural network", "neural networks"],
    "nlp": ["nlp", "natural language processing"],
    "computer vision": ["computer vision", r"\bcv\b"],
    "llm": ["llm", "large language model", "large language models"],
    "rag": ["rag", "retrieval augmented generation", "retrieval-augmented"],
    "generative ai": ["generative ai", "genai", "gen ai"],
    "reinforcement learning": ["reinforcement learning", r"\brl\b"],
    "transformers": ["transformer", "transformers"],
    "recommendation systems": ["recommendation system", "recommender", "recsys"],
    "data science": ["data science", "data scientist"],
    "data engineering": ["data engineering", "etl", "data pipeline", "data pipelines"],
    "statistics": ["statistics", "statistical"],
    "aws": ["aws", "amazon web services"],
    "gcp": ["gcp", "google cloud"],
    "azure": ["azure"],
    "docker": ["docker"],
    "kubernetes": ["kubernetes", "k8s"],
    "kafka": ["kafka"],
    "airflow": ["airflow"],
    "mlops": ["mlops"],
    "ci/cd": ["ci/cd", "cicd", "continuous integration"],
    "git": ["git", "github", "gitlab"],
    "rest api": ["rest api", "restful", "rest apis"],
    "distributed systems": ["distributed systems", "distributed computing"],
    "a/b testing": ["a/b testing", "ab testing", "experimentation"],
    "fine-tuning": ["fine-tuning", "fine tuning", "finetune", "fine-tune"],
    "prompt engineering": ["prompt engineering", "prompting"],
    "vector database": ["vector database", "vector db", "pinecone", "weaviate", "faiss"],
    "model deployment": ["model deployment", "model serving", "inference"],
    "feature engineering": ["feature engineering"],
    "time series": ["time series", "time-series", "forecasting"],
}


def _compile(patterns: list[str]) -> list[re.Pattern]:
    out = []
    for p in patterns:
        # A raw regex token (already contains a backslash) is used as-is; a plain
        # phrase is wrapped in word boundaries.
        rx = p if "\\" in p else r"\b" + re.escape(p) + r"\b"
        out.append(re.compile(rx, re.I))
    return out


_COMPILED = {canon: _compile(pats) for canon, pats in VOCAB.items() if pats}


def _present(text: str, canon: str) -> bool:
    return any(rx.search(text) for rx in _COMPILED.get(canon, []))


def build_resume_text(profile: dict | None = None) -> str:
    """Flatten a profile into one searchable blob of everything the candidate
    can credibly claim."""
    if profile is None:
        try:
            profile = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            profile = {}
    parts: list[str] = []

    skills = profile.get("skills") or {}
    if isinstance(skills, dict):
        for items in skills.values():
            parts.extend(items if isinstance(items, list) else [str(items)])
    elif isinstance(skills, list):
        parts.extend(skills)

    for exp in profile.get("experience") or []:
        parts.append(exp.get("title", ""))
        parts.append(exp.get("company", ""))
        parts.extend(exp.get("highlights", []) or exp.get("bullets", []) or [])
        if exp.get("description"):
            parts.append(exp["description"])

    for proj in profile.get("projects") or []:
        parts.append(proj.get("name", ""))
        parts.append(proj.get("description", ""))
        parts.extend(proj.get("highlights", []) or proj.get("bullets", []) or [])
        parts.extend(proj.get("tech", []) or proj.get("technologies", []) or [])

    if profile.get("summary"):
        parts.append(profile["summary"])

    return "\n".join(str(p) for p in parts if p)


def compute_match(jd_text: str, resume_text: str) -> dict:
    """Compare a job description against resume text.

    Returns ``{score, matched, missing, jd_keywords}`` where score is the fraction
    of JD-required keywords present in the resume (0.0–1.0), and matched/missing
    are canonical keyword lists.
    """
    jd = jd_text or ""
    resume = resume_text or ""

    jd_keywords = [canon for canon in _COMPILED if _present(jd, canon)]
    matched, missing = [], []
    for kw in jd_keywords:
        (matched if _present(resume, kw) else missing).append(kw)

    total = len(jd_keywords)
    score = (len(matched) / total) if total else 0.0
    return {
        "score": round(score, 3),
        "matched": sorted(matched),
        "missing": sorted(missing),
        "jd_keywords": sorted(jd_keywords),
    }


def match_for_job(job: dict, profile: dict | None = None) -> dict:
    """Convenience: compute the ATS match for a job dict using its description."""
    return compute_match(job.get("description", ""), build_resume_text(profile))
