"""Role titles/dates in a tailored résumé must match config/profile.json exactly."""
from pipeline.resume_tailor import _restore_role_facts

PROFILE = {"experience": [{
    "company": "Amazon Web Services",
    "title": "Software Development Engineer; System Development Engineer until Apr 2025",
    "start": "Jul 2023", "end": "Jul 2025", "bullets": ["a"],
}]}


def test_llm_title_and_dates_are_reverted_bullets_kept():
    tailored = {"experience": [{
        "company": "amazon web services", "title": "Software Development Engineer",
        "start": "2023", "end": "2025", "bullets": ["reworded"],
    }]}
    exp = _restore_role_facts(tailored, PROFILE)["experience"][0]
    assert exp["title"] == PROFILE["experience"][0]["title"]
    assert (exp["company"], exp["start"], exp["end"]) == ("Amazon Web Services", "Jul 2023", "Jul 2025")
    assert exp["bullets"] == ["reworded"]


def test_unknown_company_left_alone():
    tailored = {"experience": [{"company": "Other", "title": "X", "start": "a", "end": "b"}]}
    assert _restore_role_facts(tailored, PROFILE)["experience"][0]["title"] == "X"
