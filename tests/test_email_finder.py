"""
Unit tests for pipeline.email_finder with MX lookup, SMTP probing, and Hunter.io
all mocked — no DNS or network calls.
"""

from unittest.mock import patch

import pytest

import pipeline.email_finder as ef

_PROVIDER_ENV = [
    "HUNTER_API_KEY", "PROSPEO_API_KEY", "TOMBA_API_KEY", "TOMBA_SECRET",
    "REACHER_URL", "REACHER_API_KEY",
]


@pytest.fixture(autouse=True)
def _clear_provider_env(monkeypatch):
    """Hermetic tests: no provider runs unless a test opts in by setting its key."""
    for var in _PROVIDER_ENV:
        monkeypatch.delenv(var, raising=False)


def test_candidate_patterns_ordering_and_dedupe():
    pats = ef._candidate_patterns("John", "Smith", "acme.com")
    assert pats[0] == "john.smith@acme.com"   # most common first
    assert "jsmith@acme.com" in pats
    assert "john@acme.com" in pats
    assert len(pats) == len(set(pats))         # no dupes
    assert all(p.endswith("@acme.com") for p in pats)


def test_patterns_empty_on_missing_input():
    assert ef._candidate_patterns("", "Smith", "acme.com") == []
    assert ef._candidate_patterns("John", "Smith", "") == []


def test_domain_at_sign_stripped():
    pats = ef._candidate_patterns("Jane", "Doe", "@acme.com")
    assert all("@acme.com" in p and "@@" not in p for p in pats)


def test_verified_addresses_returned_first():
    # mx resolves; first.last accepted, everything else rejected
    def probe(email, mx):
        return email == "john.smith@acme.com"
    with patch.object(ef, "_mx_host", return_value="mx.acme.com"), \
         patch.object(ef, "_smtp_probe", side_effect=probe):
        out = ef.guess_emails("John", "Smith", "acme.com")
    assert out == ["john.smith@acme.com"]


def test_all_rejected_and_no_hunter_returns_empty(monkeypatch):
    monkeypatch.delenv("HUNTER_API_KEY", raising=False)
    with patch.object(ef, "_mx_host", return_value="mx.acme.com"), \
         patch.object(ef, "_smtp_probe", return_value=False):
        assert ef.guess_emails("John", "Smith", "acme.com") == []


def test_inconclusive_probe_returns_candidates(monkeypatch):
    # probe disabled → no verification, no rejections → best-effort candidates
    monkeypatch.delenv("HUNTER_API_KEY", raising=False)
    out = ef.guess_emails("John", "Smith", "acme.com", probe=False)
    assert out == ef._candidate_patterns("John", "Smith", "acme.com")


def test_hunter_fallback_used_when_probe_finds_nothing(monkeypatch):
    monkeypatch.setenv("HUNTER_API_KEY", "key")
    with patch.object(ef, "_mx_host", return_value="mx.acme.com"), \
         patch.object(ef, "_smtp_probe", return_value=False), \
         patch.object(ef, "_hunter_lookup", return_value="real.person@acme.com") as h:
        out = ef.guess_emails("John", "Smith", "acme.com")
    assert out == ["real.person@acme.com"]
    h.assert_called_once()


def test_hunter_noop_without_key(monkeypatch):
    monkeypatch.delenv("HUNTER_API_KEY", raising=False)
    assert ef._hunter_lookup("John", "Smith", "acme.com") is None


def test_apply_pattern_tokens():
    assert ef._apply_pattern("{first}.{last}", "John", "Smith", "acme.com") == "john.smith@acme.com"
    assert ef._apply_pattern("{f}{last}", "John", "Smith", "acme.com") == "jsmith@acme.com"
    assert ef._apply_pattern("{first}", "John", "Smith", "acme.com") == "john@acme.com"


def test_apply_pattern_rejects_unknown_token():
    # Unrecognised token must not produce a malformed address.
    assert ef._apply_pattern("{middle}", "John", "Smith", "acme.com") is None
    assert ef._apply_pattern("", "John", "Smith", "acme.com") is None


def test_domain_pattern_noop_without_key(monkeypatch):
    monkeypatch.delenv("HUNTER_API_KEY", raising=False)
    assert ef._hunter_domain_pattern("acme.com") is None


def test_pattern_inference_used_when_hunter_finder_misses(monkeypatch):
    # email-finder finds nothing, but domain-search reveals the company pattern.
    monkeypatch.setenv("HUNTER_API_KEY", "key")
    with patch.object(ef, "_mx_host", return_value="mx.acme.com"), \
         patch.object(ef, "_smtp_probe", return_value=None), \
         patch.object(ef, "_hunter_lookup", return_value=None), \
         patch.object(ef, "_hunter_domain_pattern", return_value="{f}{last}"):
        out = ef.guess_emails("John", "Smith", "acme.com")
    assert out[0] == "jsmith@acme.com"          # constructed address leads
    assert "john.smith@acme.com" in out          # ranked fallbacks retained


def test_extract_email_prefers_domain_match():
    payload = {"meta": {"support": "help@prospeo.io"},
               "response": {"email": {"email": "jane.doe@acme.com"}}}
    assert ef._extract_email(payload, "acme.com") == "jane.doe@acme.com"
    # no domain hint → first email found
    assert ef._extract_email({"x": "a@b.com"}) == "a@b.com"
    assert ef._extract_email({"x": "no emails here"}) is None


def test_linkedin_url_resolves_without_domain():
    # Prospeo turns a profile URL into an email with no domain supplied.
    with patch.object(ef, "_prospeo_by_linkedin", return_value="rec@acme.com") as p:
        out = ef.guess_emails("Jane", "Doe", linkedin_url="https://www.linkedin.com/in/jane")
    assert out == ["rec@acme.com"]
    p.assert_called_once()


def test_no_domain_no_url_returns_empty():
    assert ef.guess_emails("Jane", "Doe") == []


def test_finder_waterfall_falls_through_to_prospeo(monkeypatch):
    # Hunter misses, Prospeo hits — confirms providers are chained in order.
    monkeypatch.setenv("PROSPEO_API_KEY", "key")
    with patch.object(ef, "_mx_host", return_value="mx.acme.com"), \
         patch.object(ef, "_smtp_probe", return_value=None), \
         patch.object(ef, "_hunter_lookup", return_value=None), \
         patch.object(ef, "_prospeo_finder", return_value="found@acme.com") as p, \
         patch.object(ef, "_tomba_finder", return_value="tomba@acme.com") as t:
        out = ef.guess_emails("John", "Smith", "acme.com")
    assert out == ["found@acme.com"]
    p.assert_called_once()
    t.assert_not_called()                         # short-circuits at first hit


def test_providers_noop_without_keys():
    assert ef._prospeo_by_linkedin("https://www.linkedin.com/in/x") is None
    assert ef._prospeo_finder("John", "Smith", "acme.com") is None
    assert ef._tomba_finder("John", "Smith", "acme.com") is None
    assert ef._reacher_verify("john@acme.com") is None
