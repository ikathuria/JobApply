from tracker import tracker as T


def test_max_age_days_drops_stale_jobs_and_breaks_ties_by_recency(tmp_path):
    conn = T.init_db(tmp_path / "jobs.db")
    T.upsert_jobs(conn, [
        {"title": "Old", "company": "A", "url": "https://x/old", "score": 0.9, "status": "new"},
        {"title": "Fresh", "company": "B", "url": "https://x/fresh", "score": 0.6, "status": "new"},
        {"title": "Fresher", "company": "C", "url": "https://x/fresher", "score": 0.6, "status": "new"},
    ])
    conn.execute("UPDATE jobs SET created_at = datetime('now', '-30 days') WHERE title = 'Old'")
    conn.execute("UPDATE jobs SET created_at = datetime('now', '-5 days') WHERE title = 'Fresh'")
    conn.commit()

    assert [j["title"] for j in T.get_jobs(conn, status="new")] == ["Old", "Fresher", "Fresh"]
    assert [j["title"] for j in T.get_jobs(conn, status="new", max_age_days=14)] == ["Fresher", "Fresh"]
