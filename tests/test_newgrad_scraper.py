"""
Unit tests for the newgrad-jobs.com scraper.

newgrad-jobs.com is backed by jobright.ai's JSON API, so the scraper is a plain
``requests`` client (no browser). These tests exercise the wrapper's contract —
that it targets the correct category slug and source label, and that the shared
minisite scraper's output flows through unchanged — by mocking the shared
``scrape_minisite`` so no network call is made.
"""

from unittest.mock import patch

import scrapers.newgrad_jobs_scraper as ng

REQUIRED_KEYS = {"title", "company", "url", "location", "source", "date_scraped"}

SAMPLE_ROWS = [
    {
        "title": "Machine Learning Engineer, New Grad",
        "company": "Acme AI",
        "location": "San Francisco, CA",
        "url": "https://boards.greenhouse.io/acme/jobs/123",
        "source": "newgrad-jobs.com",
        "work_mode": "Hybrid",
        "salary": "$140k-$180k",
        "season": "New Grad",
        "description": "Build LLM systems.",
        "date_scraped": "2026-06-22T00:00:00",
    },
]


def test_defaults_to_ml_ai_vertical():
    assert ng.DEFAULT_VERTICALS == ("ml_ai",)
    assert ng.SOURCE == "newgrad-jobs.com"


def test_scrape_passes_category_and_source_to_minisite():
    with patch.object(ng, "scrape_minisite", return_value=SAMPLE_ROWS) as mock:
        result = ng.scrape_newgrad_jobs(max_rows=50)

    mock.assert_called_once_with("newgrad:us:ml_ai", ng.SOURCE, 50)
    assert result == SAMPLE_ROWS


def test_multiple_verticals_are_deduplicated_by_url():
    with patch.object(ng, "scrape_minisite", return_value=SAMPLE_ROWS) as mock:
        result = ng.scrape_newgrad_jobs(max_rows=50, verticals=["ml_ai", "swe"])

    assert [c.args[0] for c in mock.call_args_list] == ["newgrad:us:ml_ai", "newgrad:us:swe"]
    assert len(result) == len({j["url"] for j in SAMPLE_ROWS})


def test_scraped_jobs_have_required_keys():
    with patch.object(ng, "scrape_minisite", return_value=SAMPLE_ROWS):
        jobs = ng.scrape_newgrad_jobs()

    assert len(jobs) >= 1
    for job in jobs:
        assert REQUIRED_KEYS <= set(job.keys())
        assert job["source"] == "newgrad-jobs.com"
        assert job["title"] and job["url"]
