"""Tests for the email reply classifier + job matcher (M20)."""

import pytest

from pipeline import reply_classifier as rc


@pytest.mark.parametrize("subject,body,expected", [
    ("Interview invitation", "Let's schedule a phone screen — your availability?", "interview"),
    ("Interview request", "The hiring manager would like to meet with you.", "interview"),
    # Confirmation whose BODY describes the process must NOT read as an interview.
    ("Thank you for your application to Veolia",
     "Your application will be reviewed by the hiring manager; if selected you'll interview with the team.",
     "applied"),
    ("Thanks for applying to NoGood", "Our process includes a video interview stage.", "applied"),
    ("Coding challenge", "Please complete the online assessment on HackerRank.", "oa"),
    ("Your application", "Unfortunately, we have decided to move forward with other candidates.", "rejection"),
    ("Great news", "We are excited to offer you the position.", "offer"),
    ("Thanks for applying", "We received your application and will be in touch.", "applied"),
    ("Ishani, your application was sent to WiCi AI", "See how you compare to others.", "applied"),
    ("Your application to AI/ML Engineer at HCLTech", "Thanks for applying.", "applied"),
    ("Newsletter", "Check out our latest blog posts.", "other"),
])
def test_classify(subject, body, expected):
    assert rc.classify(subject, body) == expected


def test_confirmation_subject_wins_over_body_boilerplate():
    # A confirmation SUBJECT is authoritative: its body routinely describes the
    # whole funnel ("we'll schedule an interview…"), which must NOT read as a real
    # interview. This is the precision guarantee for confirmation-heavy inboxes.
    cat = rc.classify(
        "Application received",
        "We received your application. Next we'll schedule an interview and may extend an offer.",
    )
    assert cat == "applied"


def test_real_interview_subject_is_interview():
    # A genuine invite announces itself in the subject → interview.
    assert rc.classify("Interview invitation", "Please pick a slot.") == "interview"


def test_rejection_body_overrides_confirmation_subject():
    # "Update on your application to X" (confirmation-ish subject) but a real
    # rejection in the body → rejection.
    assert rc.classify(
        "Your application to Acme",
        "Unfortunately, we have decided to move forward with other candidates.",
    ) == "rejection"


def test_match_company_single():
    assert rc.match_company("Loved chatting about Stripe", "r@stripe.com",
                            ["Stripe", "Databricks"]) == "Stripe"


def test_match_company_ambiguous_returns_none():
    assert rc.match_company("Stripe and Databricks both reached out", "x@y.com",
                            ["Stripe", "Databricks"]) is None


def test_match_company_none_when_absent():
    assert rc.match_company("Generic recruiting email", "x@y.com",
                            ["Stripe", "Databricks"]) is None


def test_match_company_via_domain():
    assert rc.match_company("Hello", "careers@databricks.com",
                            ["Stripe", "Databricks"]) == "Databricks"


@pytest.mark.parametrize("current,category,expected", [
    ("applied", "interview", "interview"),
    ("applied", "oa", "oa"),
    ("applied", "offer", "offer"),
    ("interview", "oa", None),          # never regress
    ("oa", "interview", "interview"),   # forward OK
    ("applied", "rejection", "rejected"),
    ("interview", "rejection", "rejected"),
    ("new", "rejection", None),         # a not-yet-applied job can't be "rejected"
    ("offer", "interview", None),       # already past
])
def test_decide_transition(current, category, expected):
    assert rc.decide_transition(current, category) == expected
