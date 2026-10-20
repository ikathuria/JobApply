"""
Resume tracks (M41): four base resumes — AI/ML Engineer, Software Engineer, Data
Scientist, ML Research Engineer — defined in ``profile.json`` under ``tracks``.

A job is mapped to a track from its title; tailoring then starts from that track's
summary, skill order, and project pool instead of the whole profile, so the LLM
picks from projects already chosen for that kind of role. The same track view also
renders the untailored base PDFs used for quick applies.
"""

import copy
import re

DEFAULT_TRACK = "ai_ml"
# One-page limits for the untailored base PDFs (tailoring picks its own).
BASE_RESUME_EXPERIENCE = 2   # most recent roles (Purdue RA, AWS)
BASE_RESUME_PROJECTS = 3
BASE_PROJECT_BULLETS = 2
BASE_SKILL_CATEGORIES = 4

# First match wins. Data science and research are checked before the AI/ML
# keywords so "Data Scientist, ML" and "Research Engineer, LLM" land on their
# own tracks; AI/ML before SWE so "Software Engineer, Applied AI" stays AI/ML.
_TRACK_PATTERNS = [
    ("data_science", r"data scien|analyst|analytics|statistic|\bquant"),
    ("research", r"research|scientist|\bphd\b"),
    ("ai_ml", r"machine learning|\bml\b|\bai\b|artificial intelligence|\bllm|genai|generative"
              r"|\bnlp\b|computer vision|deep learning|mlops|\bagent|perception"),
    ("swe", r"software|\bsde\b|developer|back-?end|front-?end|full.?stack|platform"
            r"|infrastructure|systems engineer|site reliability|devops"),
]
_COMPILED = [(track, re.compile(p, re.I)) for track, p in _TRACK_PATTERNS]


def classify_track(job: dict) -> str:
    """Track key for a job, from its title. Unmatched titles default to AI/ML,
    the primary search target."""
    title = job.get("title") or ""
    for track, pattern in _COMPILED:
        if pattern.search(title):
            return track
    return DEFAULT_TRACK


def track_profile(profile: dict, track: str) -> dict:
    """A copy of the profile narrowed to one track: its projects (in the track's
    order), its skill categories first, and its base summary. Profiles without
    ``tracks`` (or an unknown track) come back unchanged."""
    spec = (profile.get("tracks") or {}).get(track)
    if not spec:
        return profile
    view = copy.deepcopy(profile)

    by_name = {p["name"]: p for p in profile.get("projects", [])}
    view["projects"] = [by_name[n] for n in spec.get("projects", []) if n in by_name]

    skills = profile.get("skills", {})
    order = [c for c in spec.get("skill_order", []) if c in skills]
    order += [c for c in skills if c not in order]
    view["skills"] = {c: skills[c] for c in order}

    view["summary"] = spec.get("summary", "")
    view["track"] = track
    view["track_label"] = spec.get("label", track)
    return view


def spec_order(profile: dict, track: str) -> list[str]:
    """The track's skill categories that exist in the profile, in order."""
    spec = (profile.get("tracks") or {}).get(track) or {}
    skills = profile.get("skills", {})
    return [c for c in spec.get("skill_order", skills) if c in skills]


def base_resume(profile: dict, track: str) -> dict:
    """An untailored resume dict (the shape ``generate_resume_pdf`` takes) for a
    track — no LLM, straight from the profile."""
    view = track_profile(profile, track)
    resume = {k: view[k] for k in (
        "name", "email", "phone", "location", "linkedin", "github", "portfolio",
        "education", "certifications", "publications",
    )}
    resume.update({
        "summary": view.get("summary", ""),
        "experience": view.get("experience", [])[:BASE_RESUME_EXPERIENCE],
        "projects": [{"name": p["name"], "bullets": p["bullets"][:BASE_PROJECT_BULLETS]}
                     for p in view["projects"][:BASE_RESUME_PROJECTS]],
        # only the track's own categories — the rest is noise on a one-pager
        "skills": {c: view["skills"][c] for c in spec_order(profile, track)[:BASE_SKILL_CATEGORIES]},
        "track": track,
    })
    return resume
