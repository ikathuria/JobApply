"""Tests for company/role extraction from recruiting emails (M20 ingest)."""

import pytest

from pipeline import application_parser as ap


@pytest.mark.parametrize("subject,frm,company,role", [
    ("Your application to AI/ML Engineer at HCLTech", "jobs-noreply@linkedin.com", "HCLTech", "AI/ML Engineer"),
    ("Ishani, your application was sent to WiCi AI", "jobs-noreply@linkedin.com", "WiCi AI", None),
    ("Thank you for your interest in Microsoft", "careers@email.careers.microsoft.com", "Microsoft", None),
    ("Next Steps with Akuna Capital: HackerRank Challenge", "no-reply@akunacapital.com", "Akuna Capital", None),
    ("Entry-level Talent Recruiting - Cisco Application Status Update", "Cisco@myworkday.com", "Cisco", None),
    ("Thanks for your interest in PMG, Ishani", "no-reply@us.greenhouse-mail.io", "PMG", None),
])
def test_parse(subject, frm, company, role):
    out = ap.parse(subject, frm)
    assert out["company"] == company
    assert out["role"] == role


def test_ats_domain_uses_local_part():
    # myworkday.com is ATS infra; the employer is in the local part.
    assert ap.parse("Application Update", "Netflix@myworkday.com")["company"] == "Netflix"


def test_generic_sender_yields_no_company():
    assert ap.parse("Hello there", "no-reply@example.com")["company"] in (None, "Example")


def test_empty():
    assert ap.parse("", "")["company"] is None
