"""
Unit tests for the Google Careers scraper.

Mocks ``requests.get`` so no network call is made, exercising HTML-blob parsing,
field normalization / HTML-stripping, pagination (driven by ``total``), the
query x location x level fan-out, and URL-level dedup.
"""

import json
from unittest.mock import MagicMock, patch

import scrapers.google_careers as gc


def _job(job_id, title="Machine Learning Engineer", company="Google"):
    """Build a 21-field job list shaped like a ds:1 row (only used fields set)."""
    row = [None] * 21
    row[gc._FIELD["id"]] = job_id
    row[gc._FIELD["title"]] = title
    row[gc._FIELD["responsibilities"]] = [None, "<ul>\n<li>Build models</li></ul>"]
    row[gc._FIELD["qualifications"]] = [None, "<h3>Minimum</h3><ul><li>BS &amp; ML</li></ul>"]
    row[gc._FIELD["company"]] = company
    row[gc._FIELD["locations"]] = [
        ["Mountain View, CA, USA", ["addr"], "Mountain View", "94043", "CA", "US"],
        ["Bengaluru, Karnataka, India", ["addr"], "Bengaluru", "560001", "KA", "IN"],
    ]
    return row


def _resp(job_list, total):
    """Mock an HTTP response whose HTML embeds the ds:1 AF_initDataCallback blob."""
    blob = json.dumps([job_list, None, total, None])
    html = (
        "<html><body>"
        f"AF_initDataCallback({{key: 'ds:1', hash: '1', data:{blob}, sideChannel: {{}}}});"
        "</body></html>"
    )
    m = MagicMock()
    m.text = html
    m.raise_for_status.return_value = None
    return m


def test_normalize_maps_fields_and_strips_html():
    job = gc._normalize(_job("abc123"), "google-careers", "Early Career")
    assert job["title"] == "Machine Learning Engineer"
    assert job["company"] == "Google"
    assert job["url"] == "https://www.google.com/about/careers/applications/jobs/results/abc123"
    assert job["source"] == "google-careers"
    assert job["season"] == "Early Career"
    assert "Mountain View, CA, USA" in job["location"] and "Bengaluru" in job["location"]
    assert "<" not in job["description"] and "&amp;" not in job["description"]  # tags stripped, entities unescaped
    assert "BS & ML" in job["description"]  # &amp; -> &
    assert "Build models" in job["description"]
    assert {"title", "company", "url", "source", "date_scraped"} <= set(job)


def test_normalize_drops_rows_without_id_or_title():
    assert gc._normalize(_job(None), "s", "L") is None
    assert gc._normalize(_job("x", title=""), "s", "L") is None
    assert gc._normalize([1, 2, 3], "s", "L") is None  # too short


def test_pagination_walks_until_total_reached():
    page1 = [_job(f"a{i}") for i in range(20)]
    page2 = [_job(f"b{i}") for i in range(5)]
    with patch.object(gc.requests, "get", side_effect=[_resp(page1, 25), _resp(page2, 25)]) as get:
        jobs = gc.scrape_google_careers(
            queries=["ml"], locations=["United States"], target_levels=["EARLY"]
        )
    assert len(jobs) == 25
    assert get.call_count == 2
    assert get.call_args_list[0].kwargs["params"]["location"] == "United States"
    assert get.call_args_list[0].kwargs["params"]["target_level"] == "EARLY"


def test_fan_out_over_locations_and_levels_dedupes_by_url():
    # Every combination returns the SAME job — dedup should collapse to one row.
    with patch.object(gc.requests, "get", return_value=_resp([_job("same")], 1)) as get:
        jobs = gc.scrape_google_careers(
            queries=["ml"],
            locations=["United States", "India"],
            target_levels=["EARLY", "INTERN_AND_APPRENTICE"],
        )
    assert len(jobs) == 1
    assert get.call_count == 4  # 1 query x 2 locations x 2 levels


def test_max_per_query_caps_collection():
    page = [_job(f"a{i}") for i in range(20)]
    with patch.object(gc.requests, "get", return_value=_resp(page, 1000)):
        jobs = gc.scrape_google_careers(
            queries=["ml"], locations=["United States"], target_levels=["EARLY"],
            max_per_query=20,
        )
    assert len(jobs) == 20


def test_missing_ds1_blob_yields_no_jobs():
    m = MagicMock()
    m.text = "<html><body>no blob here</body></html>"
    m.raise_for_status.return_value = None
    with patch.object(gc.requests, "get", return_value=m):
        jobs = gc.scrape_google_careers(
            queries=["ml"], locations=["United States"], target_levels=["EARLY"]
        )
    assert jobs == []
