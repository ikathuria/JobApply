"""
Greenhouse ATS auto-apply handler.
Fills standard Greenhouse application forms from profile data.
"""

import logging
import time
from pathlib import Path
from playwright.sync_api import Page

logger = logging.getLogger(__name__)

# Greenhouse standard field IDs
FIELD_MAP = {
    "first_name":   "#first_name",
    "last_name":    "#last_name",
    "email":        "#email",
    "phone":        "#phone",
    "location":     "#job_application_location",
    "linkedin":     "input[placeholder*='LinkedIn']",
    "github":       "input[placeholder*='GitHub'], input[placeholder*='github']",
    "portfolio":    "input[placeholder*='portfolio'], input[placeholder*='website'], input[placeholder*='Website']",
    "resume":       "input[type='file'][name*='resume'], input[type='file'][id*='resume']",
    "cover_letter": "#cover_letter_text",
}

SPONSORSHIP_KEYWORDS = ["sponsorship", "visa", "authorized", "work authorization", "legally"]
RELOCATION_KEYWORDS  = ["relocate", "relocation"]
GRADUATION_KEYWORDS  = ["graduation", "graduate date", "degree completion"]
GPA_KEYWORDS         = ["gpa", "grade point"]


def apply(page: Page, profile: dict, resume_path: Path, cover_letter: str) -> bool:
    """
    Fill a Greenhouse application form.
    Returns True if form was successfully filled and left on review/submit page.
    """
    wa = profile.get("work_authorization", {})
    name_parts = profile["name"].split(" ", 1)
    first = name_parts[0]
    last  = name_parts[1] if len(name_parts) > 1 else ""

    try:
        _fill(page, FIELD_MAP["first_name"], first)
        _fill(page, FIELD_MAP["last_name"],  last)
        _fill(page, FIELD_MAP["email"],       profile["email"])
        _fill(page, FIELD_MAP["phone"],       profile["phone"])
        _fill(page, FIELD_MAP["location"],    profile.get("city", profile["location"]))
        _fill(page, FIELD_MAP["linkedin"],    profile.get("linkedin", ""), optional=True)
        _fill(page, FIELD_MAP["github"],      profile.get("github", ""),   optional=True)
        _fill(page, FIELD_MAP["portfolio"],   profile.get("portfolio", ""), optional=True)

        # Resume upload
        resume_input = page.query_selector(FIELD_MAP["resume"])
        if resume_input and resume_path.exists():
            resume_input.set_input_files(str(resume_path))
            logger.info(f"Uploaded resume: {resume_path.name}")
            time.sleep(1)

        # Cover letter (text area)
        if cover_letter:
            cl_el = page.query_selector(FIELD_MAP["cover_letter"])
            if cl_el:
                cl_el.fill(cover_letter)

        # Custom / screening questions
        _answer_custom_questions(page, profile, wa)

        return True

    except Exception as e:
        logger.error(f"Greenhouse fill error: {e}")
        return False


def _fill(page: Page, selector: str, value: str, optional: bool = False) -> None:
    """Fill an input field if it exists."""
    if not value:
        return
    # Try each comma-separated selector variant
    for sel in [s.strip() for s in selector.split(",")]:
        el = page.query_selector(sel)
        if el:
            el.fill(value)
            return
    if not optional:
        logger.warning(f"Field not found: {selector}")


def _answer_custom_questions(page: Page, profile: dict, wa: dict) -> None:
    """
    Try to answer common Greenhouse custom screening questions.
    Handles text inputs, selects, and radio buttons.
    """
    questions = page.query_selector_all("li.custom-question, div.custom-question, .field")
    for q in questions:
        label_el = q.query_selector("label, .label")
        if not label_el:
            continue
        label = label_el.inner_text().lower().strip()

        # Work authorization / visa
        if any(k in label for k in SPONSORSHIP_KEYWORDS):
            if "require" in label or "need" in label or "sponsor" in label:
                _answer_yes_no(q, not wa.get("requires_sponsorship_internship", False))
            elif "authorized" in label or "legally" in label:
                _answer_yes_no(q, wa.get("authorized_to_work_in_us", True))

        # Relocation
        elif any(k in label for k in RELOCATION_KEYWORDS):
            _answer_yes_no(q, wa.get("will_relocate", True))

        # Graduation date
        elif any(k in label for k in GRADUATION_KEYWORDS):
            inp = q.query_selector("input[type='text'], input[type='date']")
            if inp:
                inp.fill(wa.get("expected_graduation", "May 2027"))

        # GPA
        elif any(k in label for k in GPA_KEYWORDS):
            inp = q.query_selector("input[type='text'], input[type='number']")
            if inp:
                inp.fill(wa.get("gpa", "4.0"))

        # LinkedIn / GitHub / Website (if not already in standard fields)
        elif "linkedin" in label:
            inp = q.query_selector("input")
            if inp:
                inp.fill(profile.get("linkedin", ""))
        elif "github" in label:
            inp = q.query_selector("input")
            if inp:
                inp.fill(profile.get("github", ""))
        elif "website" in label or "portfolio" in label:
            inp = q.query_selector("input")
            if inp:
                inp.fill(profile.get("portfolio", ""))


def _answer_yes_no(container, answer_yes: bool) -> None:
    """Click Yes or No radio, or fill Yes/No in a select/input."""
    target = "yes" if answer_yes else "no"

    # Radio buttons
    for radio in container.query_selector_all("input[type='radio']"):
        label_for = radio.get_attribute("id") or ""
        aria = (radio.get_attribute("aria-label") or "").lower()
        value = (radio.get_attribute("value") or "").lower()
        label_el = container.query_selector(f"label[for='{label_for}']")
        label_text = label_el.inner_text().lower() if label_el else ""
        if target in (aria, value, label_text):
            radio.click()
            return

    # Select dropdown
    sel = container.query_selector("select")
    if sel:
        try:
            sel.select_option(label=target.capitalize())
        except Exception:
            pass
