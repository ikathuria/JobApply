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
