"""Resume tracks (M41): title → track, and the per-track profile view."""
import json
from pathlib import Path

import pytest

from pipeline.resume_tracks import (
    BASE_RESUME_PROJECTS, base_resume, classify_track, track_profile,
)

PROFILE = json.loads(Path("config/profile.json").read_text())


@pytest.mark.parametrize("title,track", [
    ("Machine Learning Engineer, New Grad", "ai_ml"),
    ("Software Engineer, Applied AI", "ai_ml"),
    ("AI Engineer (All Levels)", "ai_ml"),
    ("Software Engineer I", "swe"),
    ("Backend Engineer - Payments", "swe"),
    ("Associate Data Scientist", "data_science"),
    ("Machine Learning Analyst", "data_science"),
    ("Research Engineer, Agentic Security", "research"),
    ("Applied Scientist", "research"),
    ("Product Designer", "ai_ml"),  # unmatched → primary target
])
def test_classify_track(title, track):
    assert classify_track({"title": title}) == track


def test_every_track_references_real_projects_and_skills():
    names = {p["name"] for p in PROFILE["projects"]}
    for key, spec in PROFILE["tracks"].items():
        assert set(spec["projects"]) <= names, key
        assert set(spec["skill_order"]) <= set(PROFILE["skills"]), key


def test_track_profile_narrows_projects_and_orders_skills():
    view = track_profile(PROFILE, "swe")
    spec = PROFILE["tracks"]["swe"]
    assert [p["name"] for p in view["projects"]] == spec["projects"]
    assert list(view["skills"])[:len(spec["skill_order"])] == spec["skill_order"]
    assert view["summary"] == spec["summary"]
    assert PROFILE["projects"] != view["projects"]  # original untouched


def test_unknown_track_returns_profile_unchanged():
    assert track_profile(PROFILE, "nope") is PROFILE


def test_base_resume_has_pdf_fields_and_respects_limits():
    r = base_resume(PROFILE, "ai_ml")
    for k in ("name", "email", "summary", "experience", "projects", "skills", "education"):
        assert r[k], k
    assert len(r["projects"]) <= BASE_RESUME_PROJECTS


def test_fit_one_page_caps_sections():
    from pipeline.resume_tracks import fit_one_page
    big = {
        "experience": [{"company": c, "bullets": ["b"] * 8} for c in "ABCD"],
        "projects": [{"name": n, "bullets": ["b"] * 4} for n in "PQRS"],
        "skills": {f"c{i}": ["x"] for i in range(7)},
    }
    r = fit_one_page(big)
    assert len(r["experience"]) == 2 and all(len(e["bullets"]) <= 5 for e in r["experience"])
    assert len(r["projects"]) == 3 and all(len(p["bullets"]) == 2 for p in r["projects"])
    assert len(r["skills"]) == 4


def test_shrink_to_one_page_trims_until_it_fits():
    from pipeline.resume_tracks import shrink_to_one_page
    r = {"summary": "One. Two. Three. Four.",
         "experience": [{"company": "AWS", "bullets": ["b"] * 5}],
         "projects": [{"name": n, "bullets": ["x", "y"]} for n in "PQR"], "skills": {}}

    def size(d):
        return (len(d["summary"]) + sum(len(e["bullets"]) for e in d["experience"])
                + sum(len(p["bullets"]) for p in d["projects"]))
    out = shrink_to_one_page(r, lambda d: 1 if size(d) <= 18 else 2)
    assert out["summary"] == "One. Two."
    assert size(out) <= 18 and len(out["projects"]) == 3   # stopped as soon as it fit
