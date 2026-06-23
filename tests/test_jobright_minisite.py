"""
Unit tests for the shared jobright.ai minisite JSON-API client.

Mocks ``requests.post`` so no network call is made, exercising pagination
(driven by ``result.total``), field normalization, and URL construction.
"""

from unittest.mock import MagicMock, patch

import scrapers.jobright_minisite as jm


def _api_job(job_id, title="ML Engineer", company="Acme", **props):
    base = {"title": title, "company": company, "location": "Remote, US",
            "salary": "$120k", "workModel": "Remote", "qualifications": "Do ML.",
            "roleType": "New Grad"}
    base.update(props)
    return {"jobId": job_id, "properties": base, "postedAt": 1782153202000}


def _resp(job_list, total):
    m = MagicMock()
    m.json.return_value = {"result": {"jobList": job_list, "total": total}}
    m.raise_for_status.return_value = None
    return m


def test_normalize_maps_fields_and_builds_url():
    job = jm._normalize(_api_job("abc123"), "newgrad-jobs.com")
    assert job["title"] == "ML Engineer"
    assert job["company"] == "Acme"
    assert job["url"] == "https://jobright.ai/jobs/info/abc123"
    assert job["source"] == "newgrad-jobs.com"
    assert job["work_mode"] == "Remote"
    assert job["description"] == "Do ML."
    assert {"title", "company", "url", "source", "date_scraped"} <= set(job)


def test_normalize_drops_rows_without_id_or_title():
    assert jm._normalize({"jobId": None, "properties": {"title": "X"}}, "s") is None
    assert jm._normalize({"jobId": "x", "properties": {"title": ""}}, "s") is None


def test_pagination_walks_until_total_reached():
    page0 = [_api_job(f"a{i}") for i in range(50)]
    page1 = [_api_job(f"b{i}") for i in range(20)]
    with patch.object(jm.requests, "post", side_effect=[_resp(page0, 70), _resp(page1, 70)]) as post:
        jobs = jm.scrape_minisite("newgrad:us:ml_ai", "newgrad-jobs.com", max_rows=500)
    assert len(jobs) == 70
    assert post.call_count == 2
    # category slug is sent in the POST body
    assert post.call_args_list[0].kwargs["json"] == {"category": "newgrad:us:ml_ai"}


def test_max_rows_caps_collection():
    page = [_api_job(f"a{i}") for i in range(50)]
    with patch.object(jm.requests, "post", return_value=_resp(page, 1000)):
        jobs = jm.scrape_minisite("intern:us:ml_ai", "intern-list.com", max_rows=50)
    assert len(jobs) == 50


def test_dedupes_by_url():
    dupe = [_api_job("same"), _api_job("same")]
    with patch.object(jm.requests, "post", return_value=_resp(dupe, 2)):
        jobs = jm.scrape_minisite("intern:us:ml_ai", "intern-list.com", max_rows=50)
    assert len(jobs) == 1
