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


def test_jobright_bot_check_is_blocked_not_closed():
    from bs4 import BeautifulSoup
    from pipeline.jobright_enricher import _is_challenge
    html = "<html><head><title>Security check | Jobright</title></head><body>One quick security check</body></html>"
    assert _is_challenge(html, BeautifulSoup(html, "html.parser"))
    real = '<html><head><title>AI Engineer</title></head><script id="__NEXT_DATA__">{}</script></html>'
    assert not _is_challenge(real, BeautifulSoup(real, "html.parser"))


def test_jd_fetcher_never_returns_jobright_page_html(monkeypatch):
    import pipeline.jd_fetcher as J
    import pipeline.jobright_enricher as E

    def blocked(url, **kw):
        raise E.JobrightBlocked(url)
    monkeypatch.setattr(E, "enrich_jobright_url", blocked)
    assert J.fetch_jd("https://jobright.ai/jobs/info/abc") == ""
