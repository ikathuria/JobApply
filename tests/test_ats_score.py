"""On-demand ATS score + re-tailor loop (pipeline.ats_score), with fake LLM calls."""
import json

import pipeline.ats_score as A


def test_split_missing_only_adds_what_profile_supports():
    addable, unsupported = A.split_missing(
        ["Docker", "Kubernetes", "REST APIs", "Rust"],
        "Python, Docker, REST APIs, FastAPI",
    )
    assert addable == ["Docker", "REST APIs"]
    assert unsupported == ["Kubernetes", "Rust"]


def _fake_scores(monkeypatch, scores):
    calls = iter(scores)

    def fake_complete(system, user, max_tokens=0, model=None):
        return json.dumps({"score": next(calls), "missing_keywords": ["Docker"],
                           "suggestions": ["mention Docker"]})
    monkeypatch.setattr(A, "complete", fake_complete)
    monkeypatch.setattr(A, "build_resume_text", lambda: "Docker")


def test_stops_when_target_reached(monkeypatch):
    _fake_scores(monkeypatch, [93])
    monkeypatch.setattr(A, "tailor_resume", lambda *a, **k: (_ for _ in ()).throw(AssertionError))
    r = A.ats_check({"title": "MLE"}, "jd", {"summary": "v1"})
    assert r["history"] == [93] and not r["improved"]


def test_retailors_and_keeps_best(monkeypatch):
    _fake_scores(monkeypatch, [70, 88, 84])
    versions = iter([{"summary": "v2"}, {"summary": "v3"}])
    monkeypatch.setattr(A, "tailor_resume", lambda job, jd, feedback=None: next(versions))
    r = A.ats_check({"title": "MLE"}, "jd", {"summary": "v1"})
    assert r["history"] == [70, 88, 84]
    assert r["best"] == {"summary": "v2"} and r["report"]["score"] == 88 and r["improved"]


def test_score_is_clamped_and_json_extracted(monkeypatch):
    monkeypatch.setattr(A, "complete", lambda *a, **k: 'Here: {"score": 140, "missing_keywords": []}')
    assert A.score_resume({}, "jd", profile_text="")["score"] == 100
