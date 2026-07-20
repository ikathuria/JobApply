"""
Tests for the settings-persistence endpoints (M7). Uses a temp settings.yaml so
the real config is never touched.
"""

import yaml
import pytest
from fastapi import HTTPException

import api.main as M


@pytest.fixture
def settings_file(tmp_path, monkeypatch):
    p = tmp_path / "settings.yaml"
    p.write_text(yaml.safe_dump({
        "llm": {"provider": "groq", "groq_model": "llama-3.1-8b-instant",
                "gemini_model": "gemini-2.5-flash", "anthropic_model": "claude-sonnet-4-6"},
        "scoring": {"min_score": 0.0},
        "filters": {"require_known_sponsor": False},
        "sources": {"intern_list": {"enabled": True}, "newgrad_jobs": {"enabled": True},
                    "linkedin": {"enabled": False}},
        "keep_me": {"nested": 1},
    }))
    monkeypatch.setattr(M, "SETTINGS_PATH", p)
    return p


def test_get_settings_shape(settings_file):
    s = M.api_get_settings()
    assert s["llm"]["provider"] == "groq"
    assert s["scoring"]["min_score"] == 0.0
    assert s["filters"]["require_known_sponsor"] is False
    assert s["sources"] == {"intern_list": True, "newgrad_jobs": True}


def test_save_merges_persists_and_preserves(settings_file):
    out = M.api_save_settings(M.SettingsPatch(
        llm={"provider": "gemini"},
        scoring={"min_score": 0.5},
        filters={"require_known_sponsor": True},
        sources={"intern_list": False},
    ))
    assert out["llm"]["provider"] == "gemini"
    assert out["scoring"]["min_score"] == 0.5
    assert out["filters"]["require_known_sponsor"] is True
    assert out["sources"]["intern_list"] is False
    assert out["sources"]["newgrad_jobs"] is True         # untouched source unchanged

    on_disk = yaml.safe_load(settings_file.read_text())
    assert on_disk["llm"]["provider"] == "gemini"
    assert on_disk["llm"]["groq_model"] == "llama-3.1-8b-instant"   # other llm keys kept
    assert on_disk["keep_me"] == {"nested": 1}            # unrelated top-level key preserved
    assert on_disk["sources"]["linkedin"] == {"enabled": False}     # non-editable source preserved


def test_save_rejects_unknown_provider(settings_file):
    with pytest.raises(HTTPException) as exc:
        M.api_save_settings(M.SettingsPatch(llm={"provider": "bogus"}))
    assert exc.value.status_code == 400
