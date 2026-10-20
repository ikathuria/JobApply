"""Shared tailoring flow (pipeline.tailor_flow) — failure paths, no network/LLM."""
import pytest

import pipeline.tailor_flow as F


@pytest.fixture
def stub(monkeypatch):
    calls = {}
    monkeypatch.setattr(F, "_enrich", lambda conn, job: job)
    monkeypatch.setattr(F, "update_status", lambda conn, jid, status, **kw: calls.update(status=status))
    return calls


def test_work_auth_blocked_job_is_skipped(stub, monkeypatch):
    monkeypatch.setattr(F, "_jd_text", lambda job: "Requires an active TS/SCI clearance. " * 20)
    with pytest.raises(F.TailorError, match="work authorization"):
        F.tailor_job(None, {"id": 1, "title": "MLE", "company": "X", "status": "new"})
    assert stub["status"] == "skipped"


def test_snippet_jd_is_rejected(monkeypatch):
    import pipeline.jd_fetcher as J
    monkeypatch.setattr(J, "fetch_jd", lambda url: "")
    with pytest.raises(F.TailorError, match="full job description"):
        F._jd_text({"id": 1, "url": "u", "description": "short snippet"})


def test_ats_needs_a_tailored_resume(tmp_path, monkeypatch):
    monkeypatch.setattr(F, "ROOT", tmp_path)
    with pytest.raises(F.TailorError, match="tailor it first"):
        F.ats_job(None, {"id": 1, "title": "MLE", "company": "X", "status": "queued",
                         "resume_path": "output/resumes/1_x/resume.pdf"})


def test_job_dir_is_stable_and_safe():
    d = F.job_dir({"id": 42, "company": "Acme, Inc.", "title": "ML Engineer / New Grad"})
    assert d.name == "42_acme_inc_ml_engineer_new_grad"
