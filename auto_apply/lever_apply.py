"""
Lever ATS auto-apply handler.
"""

import logging
import time
from pathlib import Path
from playwright.sync_api import Page

logger = logging.getLogger(__name__)

SPONSORSHIP_KEYWORDS = ["sponsorship", "visa", "authorized", "legally"]
RELOCATION_KEYWORDS  = ["relocate"]
GRADUATION_KEYWORDS  = ["graduation", "graduate"]
GPA_KEYWORDS         = ["gpa", "grade point"]


def apply(page: Page, profile: dict, resume_path: Path, cover_letter: str) -> bool:
    """
    Fill a Lever application form.
    Returns True if filled successfully.
    """
    wa = profile.get("work_authorization", {})
    name_parts = profile["name"].split(" ", 1)

    try:
        _fill(page, "[data-qa='name-field'] input, input[name='name']",  profile["name"])
        _fill(page, "[data-qa='email-field'] input, input[name='email']", profile["email"])
        _fill(page, "[data-qa='phone-field'] input, input[name='phone']", profile["phone"])
        _fill(page, "input[name='org'], input[placeholder*='company'], input[placeholder*='Company']",
              profile.get("experience", [{}])[0].get("company", ""), optional=True)
        _fill(page, "input[name='urls[LinkedIn]'], input[placeholder*='LinkedIn']",
              profile.get("linkedin", ""), optional=True)
        _fill(page, "input[name='urls[GitHub]'], input[placeholder*='GitHub']",
              profile.get("github", ""), optional=True)
        _fill(page, "input[name='urls[Portfolio]'], input[placeholder*='portfolio'], input[placeholder*='website']",
              profile.get("portfolio", ""), optional=True)

        # Resume upload
        resume_input = page.query_selector("input[type='file']")
        if resume_input and resume_path.exists():
            resume_input.set_input_files(str(resume_path))
            logger.info(f"Uploaded resume: {resume_path.name}")
            time.sleep(1)

        # Cover letter
        if cover_letter:
            cl_el = page.query_selector(
                "[data-qa='additional-card'] textarea, textarea[name='comments'], textarea[placeholder*='cover']"
            )
            if cl_el:
                cl_el.fill(cover_letter)

        # Custom questions
        _answer_custom_questions(page, profile, wa)

        return True

    except Exception as e:
        logger.error(f"Lever fill error: {e}")
        return False


def _fill(page: Page, selector: str, value: str, optional: bool = False) -> None:
    if not value:
        return
    for sel in [s.strip() for s in selector.split(",")]:
        el = page.query_selector(sel)
        if el:
            el.fill(value)
            return
    if not optional:
        logger.warning(f"Lever field not found: {selector}")


def _answer_custom_questions(page: Page, profile: dict, wa: dict) -> None:
    for q in page.query_selector_all(".application-question, .custom-question"):
        label_el = q.query_selector("label, p")
        if not label_el:
            continue
        label = label_el.inner_text().lower()

        if any(k in label for k in SPONSORSHIP_KEYWORDS):
            if "require" in label or "sponsor" in label:
                _answer_yes_no(q, not wa.get("requires_sponsorship_internship", False))
            elif "authorized" in label or "legally" in label:
                _answer_yes_no(q, wa.get("authorized_to_work_in_us", True))
        elif any(k in label for k in RELOCATION_KEYWORDS):
            _answer_yes_no(q, wa.get("will_relocate", True))
        elif any(k in label for k in GRADUATION_KEYWORDS):
            inp = q.query_selector("input")
            if inp:
                inp.fill(wa.get("expected_graduation", "May 2027"))
        elif any(k in label for k in GPA_KEYWORDS):
            inp = q.query_selector("input")
            if inp:
                inp.fill(wa.get("gpa", "4.0"))


def _answer_yes_no(container, answer_yes: bool) -> None:
    target = "yes" if answer_yes else "no"
    for radio in container.query_selector_all("input[type='radio']"):
        value = (radio.get_attribute("value") or "").lower()
        label_id = radio.get_attribute("id") or ""
        label_el = container.query_selector(f"label[for='{label_id}']")
        label_text = label_el.inner_text().lower() if label_el else ""
        if target in (value, label_text):
            radio.click()
            return
    sel = container.query_selector("select")
    if sel:
        try:
            sel.select_option(label=target.capitalize())
        except Exception:
            pass
