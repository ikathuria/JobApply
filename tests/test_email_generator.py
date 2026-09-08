"""
Unit tests for pipeline.email_generator with the LLM call mocked out.

Verifies: JSON parsing (+ code-fence and 'Subject:' fallbacks), cold vs referral
prompt routing, candidate-context construction, and the {subject, body} contract.
"""

from unittest.mock import patch

import pipeline.email_generator as eg

PROFILE = {
    "name": "Ishani Kathuria",
    "linkedin": "https://linkedin.com/in/ishani-kathuria",
    "portfolio": "https://ishani.kathuria.net",
    "work_authorization": {"expected_graduation": "May 2026", "gpa": 4.0},
    "education": [{"degree": "MS Applied AI", "school": "Purdue", "gpa": 4.0}],
    "experience": [
        {"title": "SDE Intern", "company": "Amazon Web Services"},
        {"title": "AI Research Assistant", "company": "Purdue"},
    ],
    "skills": {"genai": ["RAG", "LLM"], "ml": ["PyTorch"]},
    "projects": [{"name": "TrustworthyRAG"}],
}

RECRUITER = {"name": "Jane Doe", "company": "Anthropic", "title": "Recruiter"}
JOB = {"title": "ML Engineer Intern", "company": "Anthropic", "url": "https://x"}


def test_candidate_context_includes_key_facts():
    ctx = eg._candidate_context(PROFILE)
    assert "Ishani Kathuria" in ctx
    assert "Purdue" in ctx
    assert "Amazon Web Services" in ctx
    assert "May 2026" in ctx


def test_generate_cold_returns_subject_and_body():
    fake = '{"subject": "ML Intern at Anthropic", "body": "Hi Jane, ... -Ishani"}'
    with patch.object(eg, "complete", return_value=fake) as mock:
        out = eg.generate_cold_email(RECRUITER, JOB, profile=PROFILE, email_type=eg.COLD)
    assert out == {"subject": "ML Intern at Anthropic", "body": "Hi Jane, ... -Ishani"}
    # cold prompt routed (system prompt is first positional arg)
    system_prompt = mock.call_args.args[0]
    assert "recruiter or HR" in system_prompt


def test_referral_uses_referral_prompt():
    fake = '{"subject": "Quick referral ask", "body": "Hi Jane ..."}'
    with patch.object(eg, "complete", return_value=fake) as mock:
        eg.generate_cold_email(RECRUITER, JOB, profile=PROFILE, email_type=eg.REFERRAL)
    system_prompt = mock.call_args.args[0]
    assert "CURRENT EMPLOYEE" in system_prompt
    assert "refer" in system_prompt.lower()


def test_target_phrase_prefers_explicit_then_falls_back():
    assert eg._target_phrase({"work_authorization": {"job_search_target": "SWE roles"}}) == "SWE roles"
    assert eg._target_phrase({}) == eg.DEFAULT_TARGET
    # default is not the stale "internship"-only framing
    assert "new-grad" in eg.DEFAULT_TARGET


def test_target_phrase_flows_into_system_prompt():
    fake = '{"subject": "S", "body": "B"}'
    profile = {**PROFILE, "work_authorization": {"job_search_target": "full-time new-grad AI/ML roles"}}
    with patch.object(eg, "complete", return_value=fake) as mock:
        eg.generate_cold_email(RECRUITER, JOB, profile=profile, email_type=eg.COLD)
    assert "full-time new-grad AI/ML roles" in mock.call_args.args[0]


def test_shared_context_flows_into_referral_message():
    fake = '{"subject": "S", "body": "B"}'
    with patch.object(eg, "complete", return_value=fake) as mock:
        eg.generate_cold_email(
            RECRUITER, JOB, profile=PROFILE, email_type=eg.REFERRAL,
            shared_context="we overlapped at AWS",
        )
    user_message = mock.call_args.args[1]
    assert "we overlapped at AWS" in user_message


def test_shared_context_read_from_recruiter_dict():
    fake = '{"subject": "S", "body": "B"}'
    recruiter = {**RECRUITER, "notes": "ex-AWS, now at Google"}
    with patch.object(eg, "complete", return_value=fake) as mock:
        eg.generate_cold_email(recruiter, JOB, profile=PROFILE, email_type=eg.REFERRAL)
    assert "ex-AWS, now at Google" in mock.call_args.args[1]


def test_parse_handles_code_fences():
    fenced = '```json\n{"subject": "S", "body": "B"}\n```'
    assert eg._parse(fenced) == {"subject": "S", "body": "B"}


def test_parse_tolerates_literal_newlines_in_json_body():
    # LLMs commonly emit pretty-printed JSON with real line breaks inside the
    # body string — invalid per strict JSON, but we parse it with strict=False.
    raw = '{"subject": "Hi",\n"body": "Hello David,\n\nGreat work.\n\n-Ishani"}'
    out = eg._parse(raw)
    assert out["subject"] == "Hi"
    assert out["body"].startswith("Hello David,")
    assert "-Ishani" in out["body"]
    assert '"body"' not in out["body"]  # not leaking raw JSON


def test_parse_fallback_subject_line():
    plain = "Subject: Hello there\n\nHi Jane, I'd love to chat.\n-Ishani"
    out = eg._parse(plain)
    assert out["subject"] == "Hello there"
    assert "Hi Jane" in out["body"]
    assert "Subject:" not in out["body"]


def test_parse_fallback_plain_body_no_subject():
    plain = "Hi Jane, just reaching out.\n-Ishani"
    out = eg._parse(plain)
    assert out["subject"] == ""
    assert "Hi Jane" in out["body"]


def test_job_none_is_handled():
    fake = '{"subject": "Interest in AI/ML roles", "body": "Hi Jane ..."}'
    with patch.object(eg, "complete", return_value=fake) as mock:
        out = eg.generate_cold_email(RECRUITER, None, profile=PROFILE, email_type=eg.COLD)
    assert out["subject"]
    # user message mentions the general-interest fallback
    user_message = mock.call_args.args[1]
    assert "general interest" in user_message.lower()
