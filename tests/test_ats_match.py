"""Tests for the ATS keyword-match scorer (M21)."""

from pipeline import ats_match as am


def test_compute_match_basic():
    jd = "We need Python, PyTorch, deep learning, and experience with LLMs and RAG on AWS."
    resume = "Built models in Python on AWS. Strong in deep learning."
    m = am.compute_match(jd, resume)
    assert "python" in m["matched"] and "deep learning" in m["matched"] and "aws" in m["matched"]
    assert "pytorch" in m["missing"] and "rag" in m["missing"]
    assert 0.0 < m["score"] < 1.0


def test_perfect_and_zero():
    assert am.compute_match("Python and SQL", "python sql expert")["score"] == 1.0
    assert am.compute_match("Python", "I like art history")["score"] == 0.0


def test_no_keywords_scores_zero():
    m = am.compute_match("We value teamwork and communication.", "anything")
    assert m["jd_keywords"] == [] and m["score"] == 0.0


def test_llm_alias_matches():
    # JD says "large language models", resume says "LLM" → matched via alias.
    m = am.compute_match("Experience with large language models required.", "Worked on LLM apps.")
    assert "llm" in m["matched"]


def test_build_resume_text_from_profile_dict():
    profile = {
        "skills": {"languages": ["Python", "SQL"], "ml": ["PyTorch"]},
        "experience": [{"title": "SDE", "company": "AWS", "bullets": ["Built pipelines"]}],
        "projects": [{"name": "RAG bot", "bullets": ["Used LangChain"]}],
    }
    text = am.build_resume_text(profile).lower()
    assert "python" in text and "pytorch" in text and "langchain" in text and "built pipelines" in text


def test_match_for_job_uses_description():
    job = {"description": "Python and Kubernetes required."}
    profile = {"skills": {"x": ["Python"]}}
    m = am.match_for_job(job, profile)
    assert "python" in m["matched"] and "kubernetes" in m["missing"]
