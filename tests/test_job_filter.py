"""
Unit tests for the PhD-only exclusion in pipeline.job_filter.

The rule must filter PhD-required roles while KEEPING roles that accept a
Master's ("MS or PhD", "Master's/PhD", etc.).
"""

from pipeline.job_filter import is_phd_only, score_job, filter_jobs


# ── is_phd_only ───────────────────────────────────────────────────────────────

def test_phd_required_is_flagged():
    assert is_phd_only("phd required for this research role")
    assert is_phd_only("we are seeking a doctoral candidate in machine learning")
    assert is_phd_only("must have a phd in computer science")
    assert is_phd_only("currently pursuing a phd")


def test_ms_or_phd_is_kept():
    assert not is_phd_only("open to ms or phd students in ai")
    assert not is_phd_only("master's or phd in a quantitative field")
    assert not is_phd_only("phd candidate or master's degree holder")
    assert not is_phd_only("bs/ms/phd in computer science")


def test_masters_role_is_kept():
    assert not is_phd_only("master's degree in machine learning required")
    assert not is_phd_only("pursuing an ms in computer science")


def test_non_degree_text_is_kept():
    assert not is_phd_only("ai/ml internship building rag systems")
    assert not is_phd_only("")


def test_score_zero_for_phd_only_job():
    job = {
        "title": "AI Research Intern",
        "company": "Lab",
        "description": "PhD required. Doctoral candidates only. LLM research.",
        "location": "Remote",
    }
    assert score_job(job) == 0.0


def test_score_nonzero_for_ms_or_phd_job():
    job = {
        "title": "Machine Learning Intern",
        "company": "Acme",
        "description": "Open to MS or PhD students. LLM, RAG, PyTorch.",
        "location": "Remote",
    }
    assert score_job(job) > 0.0


# ── filter_jobs auto-tagging (scrape-time) ────────────────────────────────────

def _jobs():
    return [
        {"title": "ML Intern", "company": "Acme", "url": "u1",
         "description": "MS or PhD welcome. RAG, PyTorch.", "location": "Remote"},
        {"title": "AI Research Intern", "company": "Lab", "url": "u2",
         "description": "PhD required. Doctoral candidates only.", "location": "NYC"},
    ]


def test_filter_jobs_tags_phd_only_as_skipped():
    out = filter_jobs(_jobs(), min_score=0.0)
    by_url = {j["url"]: j for j in out}
    assert by_url["u2"].get("status") == "skipped"   # PhD-only → skipped
    assert by_url["u1"].get("status") is None        # MS-or-PhD → untouched (defaults new on insert)


def test_filter_jobs_skip_phd_can_be_disabled():
    out = filter_jobs(_jobs(), min_score=0.0, skip_phd=False)
    by_url = {j["url"]: j for j in out}
    assert by_url["u2"].get("status") is None        # not tagged when disabled
