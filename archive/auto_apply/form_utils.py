"""
Shared helpers for ATS auto-apply handlers.

Every handler (Greenhouse, Lever, Ashby, SmartRecruiters, Workday, …) fills the
same kinds of fields and answers the same screening questions. Centralising the
logic here keeps the per-ATS handlers thin (just the CSS selectors that differ)
and means answers to sensitive questions — work authorization especially — are
decided in exactly one place.

All functions are defensive: a missing element or a Playwright error is logged
and swallowed so one bad field never aborts a whole application.
"""

import logging
import time
from pathlib import Path

logger = logging.getLogger(__name__)

SPONSORSHIP_KEYWORDS = ["sponsorship", "visa", "authorized", "work authorization", "legally"]
RELOCATION_KEYWORDS = ["relocate", "relocation"]
GRADUATION_KEYWORDS = ["graduation", "graduate date", "degree completion", "expected graduation"]
GPA_KEYWORDS = ["gpa", "grade point"]


def requires_sponsorship(wa: dict) -> bool:
    """Truthful answer to 'will you require sponsorship?'.

    Ishani is an F-1 student: no sponsorship for CPT internships, but H-1B
    sponsorship IS required for full-time employment. Since the target is now
    full-time new-grad roles (and most screening questions ask 'now or in the
    future'), we answer YES whenever sponsorship is required for *either* path.
    Answering 'no' on a full-time role would be false and could get an offer
    rescinded — the exact opposite of robust.
    """
    return bool(
        wa.get("requires_sponsorship_fulltime", True)
        or wa.get("requires_sponsorship_internship", False)
    )


def fill_field(page, selector: str, value: str, optional: bool = False) -> bool:
    """Fill the first matching input among comma-separated selector variants.

    Returns True if a field was filled. Never raises.
    """
    if not value:
        return False
    for sel in [s.strip() for s in selector.split(",") if s.strip()]:
        try:
            el = page.query_selector(sel)
        except Exception:
            continue
        if el:
            try:
                el.fill(value)
                return True
            except Exception as e:
                logger.debug(f"fill failed on {sel!r}: {e}")
                continue
    if not optional:
        logger.warning(f"Field not found: {selector}")
    return False


def upload_resume(page, resume_path: Path, selector: str = "input[type='file']") -> bool:
    """Attach the resume PDF to the first matching file input. Never raises."""
    if not resume_path or not Path(resume_path).exists():
        return False
    for sel in [s.strip() for s in selector.split(",") if s.strip()]:
        try:
            el = page.query_selector(sel)
        except Exception:
            continue
        if el:
            try:
                el.set_input_files(str(resume_path))
                logger.info(f"Uploaded resume: {Path(resume_path).name}")
                time.sleep(1)
                return True
            except Exception as e:
                logger.debug(f"resume upload failed on {sel!r}: {e}")
                continue
    logger.warning("Resume file input not found.")
    return False


def answer_yes_no(container, answer_yes: bool) -> bool:
    """Click a Yes/No radio (or pick it in a <select>) within a container.

    Returns True if an answer was registered. Never raises.
    """
    target = "yes" if answer_yes else "no"
    try:
        radios = container.query_selector_all("input[type='radio']")
    except Exception:
        radios = []
    for radio in radios:
        aria = (radio.get_attribute("aria-label") or "").lower()
        value = (radio.get_attribute("value") or "").lower()
        rid = radio.get_attribute("id") or ""
        label_text = ""
        if rid:
            lbl = container.query_selector(f"label[for='{rid}']")
            if lbl:
                label_text = lbl.inner_text().lower()
        if target in (aria, value, label_text) or label_text.strip() == target:
            try:
                radio.click()
                return True
            except Exception:
                continue
    sel = None
    try:
        sel = container.query_selector("select")
    except Exception:
        pass
    if sel:
        for opt in (target.capitalize(), target, target.upper()):
            try:
                sel.select_option(label=opt)
                return True
            except Exception:
                continue
    return False


def _q_text(container) -> str:
    """Best-effort visible label/question text for a form container."""
    for sel in ("label", ".label", "legend", "p", "span.t-bold", "span", "div"):
        try:
            el = container.query_selector(sel)
        except Exception:
            el = None
        if el:
            try:
                txt = el.inner_text().strip()
            except Exception:
                txt = ""
            if txt:
                return txt.lower()
    return ""


def answer_custom_questions(page, profile: dict, wa: dict, container_selector: str) -> int:
    """Answer common screening questions inside each matched container.

    Handles work authorization / sponsorship, relocation, graduation date, GPA,
    and LinkedIn/GitHub/portfolio links. Returns the number of questions it
    attempted to answer. Never raises.
    """
    try:
        containers = page.query_selector_all(container_selector)
    except Exception:
        containers = []
    answered = 0
    for q in containers:
        label = _q_text(q)
        if not label:
            continue

        if any(k in label for k in SPONSORSHIP_KEYWORDS):
            if "require" in label or "need" in label or "sponsor" in label:
                # "Do you require sponsorship?" — truthful yes for full-time.
                answered += answer_yes_no(q, requires_sponsorship(wa))
            elif "authorized" in label or "legally" in label or "eligible" in label:
                # "Are you authorized to work?" — yes (F-1 on CPT/OPT).
                answered += answer_yes_no(q, wa.get("authorized_to_work_in_us", True))
        elif any(k in label for k in RELOCATION_KEYWORDS):
            answered += answer_yes_no(q, wa.get("will_relocate", True))
        elif any(k in label for k in GRADUATION_KEYWORDS):
            answered += _fill_in_container(q, wa.get("expected_graduation", "May 2027"))
        elif any(k in label for k in GPA_KEYWORDS):
            answered += _fill_in_container(q, wa.get("gpa", "4.0"))
        elif "linkedin" in label:
            answered += _fill_in_container(q, profile.get("linkedin", ""))
        elif "github" in label:
            answered += _fill_in_container(q, profile.get("github", ""))
        elif "website" in label or "portfolio" in label:
            answered += _fill_in_container(q, profile.get("portfolio", ""))
    return answered


def _fill_in_container(container, value: str) -> int:
    """Fill the first text input/textarea inside a container. Returns 0/1."""
    if not value:
        return 0
    try:
        el = container.query_selector(
            "input[type='text'], input[type='date'], input[type='number'], "
            "input:not([type]), textarea"
        )
    except Exception:
        el = None
    if el:
        try:
            el.fill(value)
            return 1
        except Exception:
            return 0
    return 0
