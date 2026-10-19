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


# ── M18: full-time new-grad retarget ──────────────────────────────────────────

def test_new_grad_roles_score_nonzero():
    """The core M18 fix: full-time new-grad / entry-level roles used to score
    0.0 because the role gate only accepted intern keywords."""
    new_grad = {
        "title": "Machine Learning Engineer, New Grad", "company": "Acme",
        "description": "LLM, RAG, PyTorch, deep learning.", "location": "USA",
    }
    entry = {
        "title": "Entry-Level AI Engineer", "company": "Acme",
        "description": "generative ai, langchain", "location": "USA",
    }
    assert score_job(new_grad) > 0.0
    assert score_job(entry) > 0.0


def test_newgrad_feed_source_accepted_without_keyword():
    """A generic-titled role from our new-grad feed passes the role gate by
    source; the same role from an unknown source (no role keyword) does not."""
    from_feed = {
        "title": "Software Engineer", "company": "Acme",
        "description": "work on ML models, python, pytorch", "location": "USA",
        "source": "newgrad-jobs.com",
    }
    no_feed = {**from_feed, "source": "somewhere-else.com"}
    assert score_job(from_feed) > 0.0
    assert score_job(no_feed) == 0.0


def test_over_senior_role_is_penalized_not_zeroed():
    """A senior role that leaks in via the feed is penalized (sinks) but kept;
    a non-senior equivalent from the same feed scores higher."""
    base_desc = "llm rag pytorch deep learning generative ai"
    senior = {
        "title": "Senior ML Engineer", "company": "Acme",
        "description": base_desc, "location": "USA", "source": "newgrad-jobs.com",
    }
    junior = {**senior, "title": "ML Engineer, New Grad"}
    s_senior, s_junior = score_job(senior), score_job(junior)
    assert 0.0 < s_senior < s_junior


def test_multi_year_experience_requirement_penalized():
    job = {
        "title": "ML Engineer", "company": "Acme",
        "description": "requires 7+ years experience. llm rag pytorch generative ai",
        "location": "USA", "source": "newgrad-jobs.com",
    }
    plain = {**job, "description": "llm rag pytorch generative ai"}
    assert 0.0 < score_job(job) < score_job(plain)


def test_junior_title_overrides_senior_word():
    """A genuine new-grad role whose title contains a senior-ish word (e.g.
    'Architect') is NOT penalized, because the junior signal wins."""
    job = {
        "title": "New Grad Solutions Architect", "company": "Acme",
        "description": "llm rag pytorch generative ai", "location": "USA",
    }
    # scores as a full-strength new-grad role (no seniority multiplier)
    assert score_job(job) > 0.5


def test_intern_and_coop_still_score():
    """Regression: internships and co-ops remain in scope for CPT."""
    intern = {
        "title": "Machine Learning Intern", "company": "Acme",
        "description": "RAG, PyTorch.", "location": "Remote",
    }
    coop = {
        "title": "AI Co-op", "company": "Acme",
        "description": "nlp, transformers", "location": "USA",
    }
    assert score_job(intern) > 0.0
    assert score_job(coop) > 0.0


# ── work-authorization exclusions (F-1 / OPT) ─────────────────────────────────

from pipeline.job_filter import work_auth_blocker  # noqa: E402


def test_work_auth_blockers_from_real_jds():
    for text in [
        "Active TS/SCI clearance with CI Poly",
        "US citizenship and eligibility to obtain a US security clearance",
        "Universal Corporation is unable to provide visa sponsorship for this position",
        "The company will not sponsor employment visas for this role",
        "Visa sponsorship is not offered for this role",
        "authorized to work for any company without sponsorship",
        "must be legally authorized to work permanently in the country",
        "Signals\nGrowth Opportunities, No H1B, Security Clearance Required",
        "Be a U.S. Person (U.S. citizen or permanent resident)",
        "This role is subject to ITAR",
    ]:
        assert work_auth_blocker(text), text


def test_opt_compatible_text_is_not_blocked():
    for text in [
        "Candidates must be authorized to work in the United States",
        "We consider all applicants without regard to race or citizenship status",
        "Experience with military or defense customers",   # 'itar' inside a word
        "a famous person once said",                       # 'us person' inside words
        "Signals\nH1B Sponsor Likely",
        "We sponsor visas for qualified candidates",
    ]:
        assert work_auth_blocker(text) is None, text


def test_score_zero_for_clearance_job():
    job = {"title": "Machine Learning Engineer, New Grad", "company": "X",
           "description": "LLM work. Requires an active Secret clearance."}
    assert score_job(job) == 0.0
