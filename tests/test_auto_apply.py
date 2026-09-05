"""
Tests for the auto-apply runner's ATS detection and each handler's fill path.

No real browser is launched — a permissive fake Page records what the handler
would have filled/uploaded. Playwright itself isn't required (the modules import
cleanly without it), so these run in CI and locally.
"""

import pytest

from auto_apply import apply_runner
from auto_apply import (
    ashby_apply, greenhouse_apply, lever_apply,
    smartrecruiters_apply, workday_apply,
)

PROFILE = {
    "name": "Ishani Kathuria",
    "email": "ishani@example.com",
    "phone": "555-0100",
    "location": "Hammond, IN",
    "city": "Hammond",
    "state": "IN",
    "zip": "46323",
    "linkedin": "https://linkedin.com/in/ishani",
    "github": "https://github.com/ikathuria",
    "portfolio": "https://ishani.dev",
    "experience": [{"company": "Amazon"}],
    "work_authorization": {
        "authorized_to_work_in_us": True,
        "requires_sponsorship_internship": False,
        "requires_sponsorship_fulltime": True,
        "will_relocate": True,
        "expected_graduation": "May 2027",
        "gpa": "4.0",
    },
}


class _Rec:
    def __init__(self):
        self.filled = None
        self.files = None

    def fill(self, v):
        self.filled = v

    def set_input_files(self, p):
        self.files = p

    def is_visible(self):
        return True


class AutoPage:
    """Returns a recording element for any selector except those in `missing`."""

    def __init__(self, missing=()):
        self.missing = set(missing)
        self.made = {}

    def query_selector(self, sel):
        if sel in self.missing:
            return None
        return self.made.setdefault(sel, _Rec())

    def query_selector_all(self, sel):
        return []


# ---- ATS detection ---------------------------------------------------------

@pytest.mark.parametrize("url,expected", [
    ("https://boards.greenhouse.io/acme/jobs/123", "greenhouse"),
    ("https://jobs.lever.co/acme/abc", "lever"),
    ("https://www.linkedin.com/jobs/view/123", "linkedin"),
    ("https://jobs.ashbyhq.com/acme/xyz", "ashby"),
    ("https://jobs.smartrecruiters.com/acme/123", "smartrecruiters"),
    ("https://acme.wd1.myworkdayjobs.com/en-US/careers", "workday"),
    ("https://careers.example.com/apply", "unknown"),
])
def test_detect_ats(url, expected):
    assert apply_runner._detect_ats(url) == expected


def test_new_ats_are_supported_not_unsupported():
    for ats in ("ashby", "smartrecruiters", "workday"):
        assert ats in apply_runner.SUPPORTED_ATS
        assert ats not in apply_runner.UNSUPPORTED_ATS


# ---- handler fill paths ----------------------------------------------------

def _resume(tmp_path):
    p = tmp_path / "resume.pdf"
    p.write_text("pdf")
    return p


@pytest.mark.parametrize("mod", [
    greenhouse_apply, lever_apply, ashby_apply, smartrecruiters_apply,
])
def test_handler_fills_and_uploads(mod, tmp_path):
    page = AutoPage()
    resume = _resume(tmp_path)
    assert mod.apply(page, PROFILE, resume, "My cover letter") is True
    # The resume file input was populated on at least one selector.
    assert any(getattr(el, "files", None) == str(resume) for el in page.made.values())
    # Something identity-like got filled.
    assert any(getattr(el, "filled", None) for el in page.made.values())


def test_workday_fills_when_on_form(tmp_path):
    # No auth-gate controls present → treated as the "My Information" step.
    page = AutoPage(missing=set(workday_apply._GATE_SELECTORS))
    resume = _resume(tmp_path)
    assert workday_apply.apply(page, PROFILE, resume, "") is True
    assert any(getattr(el, "filled", None) for el in page.made.values())


def test_workday_stops_at_auth_gate(tmp_path):
    # Every gate selector present & visible → handler must NOT fill; returns False.
    page = AutoPage()  # gate selectors resolve to visible elements
    assert workday_apply.apply(page, PROFILE, _resume(tmp_path), "") is False


def test_workday_returns_false_when_no_form(tmp_path):
    # Gate absent AND no identity fields → not on the right step.
    identity = [
        "[data-automation-id='legalNameSection_firstName']",
        "input[data-automation-id='firstName']",
        "[data-automation-id='legalNameSection_lastName']",
        "input[data-automation-id='lastName']",
    ]
    page = AutoPage(missing=set(workday_apply._GATE_SELECTORS) | set(identity))
    assert workday_apply.apply(page, PROFILE, _resume(tmp_path), "") is False
