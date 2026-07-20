"""
Tests for offer/interview email notifications (M10). The Gmail sender is mocked,
so no SMTP and no credentials are needed.
"""

import yaml
import pytest

import api.main as M
from tracker import tracker as T
from pipeline import email_sender


@pytest.fixture
def env(tmp_path, monkeypatch):
    c = T.init_db(tmp_path / "notif.db")
    monkeypatch.setattr(M, "_conn", c)
    sp = tmp_path / "settings.yaml"
    sp.write_text(yaml.safe_dump({
        "notifications": {"on_offer": True, "on_interview": False, "email_to": "me@x.com"},
    }))
    monkeypatch.setattr(M, "SETTINGS_PATH", sp)
    sent = []
    monkeypatch.setattr(email_sender, "send_email",
                        lambda to, sub, body: sent.append((to, sub, body)) or True)
    yield c, sent
    c.close()


def _add_job(conn, status):
    T.upsert_jobs(conn, [{"title": "MLE", "company": "Acme", "url": "n1", "status": status}])
    return conn.execute("SELECT id FROM jobs WHERE url='n1'").fetchone()["id"]


def test_offer_transition_sends_email(env):
    conn, sent = env
    jid = _add_job(conn, "applied")
    M.api_patch_job(jid, M.JobPatch(status="offer"))
    assert len(sent) == 1
    to, subject, _ = sent[0]
    assert to == "me@x.com" and "OFFER" in subject and "Acme" in subject


def test_interview_toggle_off_no_email(env):
    conn, sent = env                 # on_interview is False in the fixture
    jid = _add_job(conn, "applied")
    M.api_patch_job(jid, M.JobPatch(status="interview"))
    assert sent == []


def test_no_email_when_status_unchanged(env):
    conn, sent = env
    jid = _add_job(conn, "offer")    # already at offer
    M.api_patch_job(jid, M.JobPatch(status="offer", notes="just a note"))
    assert sent == []


def test_non_milestone_transition_no_email(env):
    conn, sent = env
    jid = _add_job(conn, "new")
    M.api_patch_job(jid, M.JobPatch(status="applied"))   # applied isn't a milestone
    assert sent == []
