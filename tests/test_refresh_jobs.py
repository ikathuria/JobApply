from pipeline.jobright_enricher import JobrightBlocked, JobrightEnrichment
from pipeline.refresh_jobs import refresh_new_jobs
from tracker import tracker as T

JR = "https://jobright.ai/jobs/info/"


def _db(tmp_path):
    conn = T.init_db(tmp_path / "jobs.db")
    T.upsert_jobs(conn, [
        {"title": "Closed", "company": "A", "url": JR + "a", "score": 0.9, "status": "new"},
        {"title": "Open", "company": "B", "url": JR + "b", "score": 0.8, "status": "new"},
        {"title": "NoLink", "company": "C", "url": JR + "c", "score": 0.7, "status": "new"},
        {"title": "Direct", "company": "D", "url": "https://d.com/jobs/1", "score": 0.95, "status": "new"},
    ])
    return conn


def _by_title(conn):
    return {r["title"]: dict(r) for r in conn.execute("SELECT * FROM jobs")}


def test_skips_closed_and_relinks_open_jobs(tmp_path):
    conn = _db(tmp_path)
    seen = []

    def fake(url):
        seen.append(url)
        if url.endswith("a"):
            return JobrightEnrichment(is_closed=True, closed_reason="job is closed")
        if url.endswith("b"):
            return JobrightEnrichment(employer_url="https://careers.b.com/123")
        return JobrightEnrichment()

    counts = refresh_new_jobs(conn, delay=0, enrich=fake)
    jobs = _by_title(conn)

    assert counts == {"checked": 3, "closed": 1, "relinked": 1, "blocked": False}
    assert JR + "c" in seen and "https://d.com/jobs/1" not in seen
    assert jobs["Closed"]["status"] == "skipped" and "closed" in jobs["Closed"]["notes"]
    assert jobs["Open"]["url"] == "https://careers.b.com/123"
    assert jobs["Open"]["source_url"] == JR + "b" and jobs["Open"]["status"] == "new"
    assert jobs["NoLink"]["url"] == JR + "c" and jobs["NoLink"]["status"] == "new"


def test_stops_on_rate_limit_without_skipping(tmp_path):
    conn = _db(tmp_path)

    def blocked(url):
        raise JobrightBlocked(url)

    counts = refresh_new_jobs(conn, delay=0, enrich=blocked)
    assert counts["blocked"] and counts["checked"] == 0
    assert all(j["status"] == "new" for j in _by_title(conn).values())
