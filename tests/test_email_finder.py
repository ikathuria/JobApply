"""
Unit tests for pipeline.email_finder with MX lookup, SMTP probing, and Hunter.io
all mocked — no DNS or network calls.
"""

from unittest.mock import patch

import pipeline.email_finder as ef


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
