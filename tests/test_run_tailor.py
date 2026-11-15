import main
import pipeline.tailor_flow as tf
from tracker import tracker as T


def test_run_tailor_skips_intern_titles_before_applying_limit(tmp_path, monkeypatch):
    conn = T.init_db(tmp_path / "jobs.db")
    T.upsert_jobs(conn, [
        {"title": "ML Engineer Intern", "company": "A", "url": "https://x/1", "score": 0.95, "status": "new"},
        {"title": "Software Engineering Internship", "company": "B", "url": "https://x/2", "score": 0.9, "status": "new"},
        {"title": "Data Science Co-op", "company": "C", "url": "https://x/3", "score": 0.85, "status": "new"},
        {"title": "Internal Tools Engineer", "company": "D", "url": "https://x/4", "score": 0.8, "status": "new"},
        {"title": "Software Engineer, New Grad", "company": "E", "url": "https://x/5", "score": 0.7, "status": "new"},
        {"title": "MLE I", "company": "F", "url": "https://x/6", "score": 0.6, "status": "new"},
    ])
    monkeypatch.setattr(main, "_open_db", lambda: conn)
    tailored = []

    def fake_tailor(_conn, job, cover_letter=False):
        tailored.append(job["title"])
        return {"message": "ok", "resume_path": "x.pdf"}

    monkeypatch.setattr(tf, "tailor_job", fake_tailor)
    main.run_tailor(limit=2)

    assert tailored == ["Internal Tools Engineer", "Software Engineer, New Grad"]
