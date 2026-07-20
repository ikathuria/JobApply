"""
Tests for the visa-sponsorship-history filter (M17).
"""

from pipeline.sponsorship import is_known_sponsor, sponsor_score, _normalize
from pipeline.job_filter import score_job, filter_jobs


# ── normalization + matching ──────────────────────────────────────────────────

def test_known_sponsor_exact_and_suffixed():
    assert is_known_sponsor("Amazon")
    assert is_known_sponsor("Amazon.com, Inc.")          # punctuation + suffix
    assert is_known_sponsor("Google LLC")
    assert is_known_sponsor("NVIDIA Corporation")


def test_token_subset_match():
    assert is_known_sponsor("Amazon Web Services")        # matched by "Amazon"
    assert is_known_sponsor("Meta Platforms, Inc.")


def test_unknown_company_is_not_a_sponsor():
    assert not is_known_sponsor("Totally Unknown Startup XYZ")
    assert not is_known_sponsor("")
    assert not is_known_sponsor(None)


def test_no_false_positive_from_substring():
    # "Meta" is a sponsor, but a token-subset match must not flag "Metabolic".
    assert not is_known_sponsor("Metabolic Labs")


def test_normalize_strips_suffixes():
    assert _normalize("Amazon.com, Inc.") == "amazon"
    assert _normalize("Two Sigma") == "two sigma"


def test_sponsor_score_is_binary():
    assert sponsor_score("Google") == 1.0
    assert sponsor_score("Nobody Co") == 0.0


# ── scoring integration ───────────────────────────────────────────────────────

def test_known_sponsor_gets_scoring_boost():
    base = {
        "title": "Machine Learning Engineer, New Grad",
        "description": "pytorch deep learning", "location": "USA",
    }
    sponsor = {**base, "company": "NVIDIA"}
    unknown = {**base, "company": "Obscure Local Co"}
    assert score_job(sponsor) > score_job(unknown)        # +0.10 sponsor boost


# ── opt-in hard filter ────────────────────────────────────────────────────────

def _jobs():
    return [
        {"title": "ML Engineer, New Grad", "company": "Amazon", "url": "s1",
         "description": "pytorch llm", "location": "USA"},
        {"title": "ML Engineer, New Grad", "company": "Obscure Local Co", "url": "s2",
         "description": "pytorch llm", "location": "USA"},
    ]


def test_require_sponsor_tags_non_sponsors_skipped():
    out = filter_jobs(_jobs(), require_sponsor=True)
    by_url = {j["url"]: j for j in out}
    assert by_url["s1"].get("status") is None             # known sponsor → untouched
    assert by_url["s2"].get("status") == "skipped"        # non-sponsor → skipped


def test_require_sponsor_off_by_default():
    out = filter_jobs(_jobs())
    by_url = {j["url"]: j for j in out}
    assert by_url["s2"].get("status") is None             # not tagged when off
