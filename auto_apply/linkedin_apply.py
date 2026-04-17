"""
LinkedIn Easy Apply handler.
Requires an active LinkedIn Playwright session (already logged in).
"""

import logging
import time
from pathlib import Path
from playwright.sync_api import Page

logger = logging.getLogger(__name__)

EASY_APPLY_BTN  = "button.jobs-apply-button, button[aria-label*='Easy Apply']"
NEXT_BTN        = "button[aria-label='Continue to next step']"
REVIEW_BTN      = "button[aria-label='Review your application']"
SUBMIT_BTN      = "button[aria-label='Submit application']"
RESUME_LABEL    = "label[for*='resume'], button[aria-label*='upload']"
DISMISS_BTN     = "button[aria-label='Dismiss']"

SPONSORSHIP_KEYWORDS = ["sponsor", "visa", "authorized", "authorization"]
RELOCATION_KEYWORDS  = ["relocat"]
GRADUATION_KEYWORDS  = ["graduat"]
GPA_KEYWORDS         = ["gpa", "grade point"]


def apply(page: Page, profile: dict, resume_path: Path, cover_letter: str) -> bool:
    """
    Drive a LinkedIn Easy Apply flow from an already-open job page.
    Stops at the final review step — user must press Enter to submit.
    Returns True if reached review step.
    """
    wa = profile.get("work_authorization", {})

    # Click Easy Apply
    btn = page.query_selector(EASY_APPLY_BTN)
    if not btn:
        logger.warning("Easy Apply button not found on page")
        return False
    btn.click()
    time.sleep(2)

    max_steps = 10
    for step in range(max_steps):
        # Check for review/submit step
        if page.query_selector(SUBMIT_BTN):
            logger.info("Reached LinkedIn Easy Apply review page — waiting for user confirmation")
            return True

        if page.query_selector(REVIEW_BTN):
            page.click(REVIEW_BTN)
            time.sleep(1)
            return True

        # Fill current step fields
        _fill_contact(page, profile)
        _upload_resume(page, resume_path)
        _fill_cover_letter(page, cover_letter)
        _answer_questions(page, profile, wa)

        # Advance to next step
        next_btn = page.query_selector(NEXT_BTN)
        if next_btn:
            next_btn.click()
            time.sleep(2)
        else:
            break

    return False


def _fill_contact(page: Page, profile: dict) -> None:
    name_parts = profile["name"].split(" ", 1)
    _try_fill(page, "input[id*='firstName'], input[aria-label*='First name']", name_parts[0])
    _try_fill(page, "input[id*='lastName'], input[aria-label*='Last name']",
              name_parts[1] if len(name_parts) > 1 else "")
    _try_fill(page, "input[id*='phoneNumber'], input[aria-label*='Phone']", profile["phone"])
    _try_fill(page, "input[id*='city'], input[aria-label*='City']", profile.get("city", "Hammond"))


def _upload_resume(page: Page, resume_path: Path) -> None:
    if not resume_path or not resume_path.exists():
        return
    inp = page.query_selector("input[type='file']")
    if inp:
        inp.set_input_files(str(resume_path))
        logger.info(f"Uploaded resume: {resume_path.name}")
        time.sleep(1)


def _fill_cover_letter(page: Page, cover_letter: str) -> None:
    if not cover_letter:
        return
    for sel in ["textarea[id*='cover'], textarea[aria-label*='cover']",
                "textarea[id*='message']", "textarea"]:
        el = page.query_selector(sel)
        if el:
            label_el = page.query_selector(f"label[for='{el.get_attribute(\"id\")}']")
            label = (label_el.inner_text() if label_el else "").lower()
            if "cover" in label or not label:
                el.fill(cover_letter)
                return


def _answer_questions(page: Page, profile: dict, wa: dict) -> None:
    for fieldset in page.query_selector_all("div.jobs-easy-apply-form-section__grouping, div[data-test-form-element]"):
        label_el = fieldset.query_selector("label, legend, span.t-bold")
        if not label_el:
            continue
        label = label_el.inner_text().lower()

        if any(k in label for k in SPONSORSHIP_KEYWORDS):
            if "require" in label or "sponsor" in label:
                _select_yes_no(fieldset, not wa.get("requires_sponsorship_internship", False))
            else:
                _select_yes_no(fieldset, wa.get("authorized_to_work_in_us", True))
        elif any(k in label for k in RELOCATION_KEYWORDS):
            _select_yes_no(fieldset, wa.get("will_relocate", True))
        elif any(k in label for k in GRADUATION_KEYWORDS):
            inp = fieldset.query_selector("input")
            if inp:
                inp.fill(wa.get("expected_graduation", "May 2027"))
        elif any(k in label for k in GPA_KEYWORDS):
            inp = fieldset.query_selector("input")
            if inp:
                inp.fill(wa.get("gpa", "4.0"))


def _try_fill(page: Page, selector: str, value: str) -> None:
    if not value:
        return
    for sel in [s.strip() for s in selector.split(",")]:
        el = page.query_selector(sel)
        if el and not el.get_attribute("disabled"):
            current = el.input_value() if el.input_value else ""
            if not current:
                el.fill(value)
            return


def _select_yes_no(container, answer_yes: bool) -> None:
    target = "yes" if answer_yes else "no"
    for radio in container.query_selector_all("input[type='radio']"):
        value = (radio.get_attribute("value") or "").lower()
        if target == value:
            radio.click()
            return
    sel = container.query_selector("select")
    if sel:
        try:
            sel.select_option(label=target.capitalize())
        except Exception:
            pass
