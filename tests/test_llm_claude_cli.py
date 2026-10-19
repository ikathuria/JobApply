"""claude_cli provider: subscription-billed, so it must never leak an API key."""
import json
from types import SimpleNamespace

import pipeline.llm_client as L


def test_claude_cli_strips_api_key_and_sets_config_dir(monkeypatch):
    seen = {}

    def fake_run(cmd, input, env, **kw):
        seen.update(cmd=cmd, input=input, env=env)
        return SimpleNamespace(returncode=0, stderr="",
                               stdout=json.dumps({"is_error": False, "result": "hi"}))

    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setattr(L, "_config_cache", {"provider": "claude_cli",
                                             "claude_cli_config_dir": "/tmp/acct"})
    monkeypatch.setattr("shutil.which", lambda _: "/bin/claude")
    monkeypatch.setattr("subprocess.run", fake_run)

    assert L.complete("sys", "user") == "hi"
    assert "ANTHROPIC_API_KEY" not in seen["env"]
    assert seen["env"]["CLAUDE_CONFIG_DIR"] == "/tmp/acct"
    assert seen["input"] == "user"
    assert seen["cmd"][seen["cmd"].index("--system-prompt") + 1] == "sys"
