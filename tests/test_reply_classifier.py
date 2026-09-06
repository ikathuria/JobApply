"""Tests for the email reply classifier + job matcher (M20)."""

import pytest

from pipeline import reply_classifier as rc


@pytest.mark.parametrize("subject,body,expected", [
    ("Interview invitation", "Let's schedule a phone screen — your availability?", "interview"),
    ("Next steps", "The hiring manager would like to meet with you.", "interview"),
    ("Coding challenge", "Please complete the online assessment on HackerRank.", "oa"),
    ("Your application", "Unfortunately, we have decided to move forward with other candidates.", "rejection"),
    ("Great news", "We are excited to offer you the position.", "offer"),
    ("Thanks for applying", "We received your application and will be in touch.", "other"),
    ("Newsletter", "Check out our latest blog posts.", "other"),
])
def test_classify(subject, body, expected):
    assert rc.classify(subject, body) == expected


def test_confirmation_with_strong_signal_is_not_other():
    # "application received" but also a real interview ask → interview wins.
    cat = rc.classify(
        "Application received",
        "We received your application. We'd like to schedule an interview — availability?",
    )
    assert cat == "interview"


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
