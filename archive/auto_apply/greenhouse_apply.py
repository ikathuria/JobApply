"""
Greenhouse ATS auto-apply handler.
Fills standard Greenhouse application forms from profile data.
"""

import logging
from pathlib import Path

try:  # Page is used only as a type hint; don't require Playwright to import.
    from playwright.sync_api import Page
except ImportError:  # pragma: no cover
    Page = object  # type: ignore

from auto_apply import form_utils as fu

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
    "resume":       "input[type='file'][name*='resume'], input[type='file'][id*='resume'], input[type='file']",
    "cover_letter": "#cover_letter_text",
}


def apply(page: Page, profile: dict, resume_path: Path, cover_letter: str) -> bool:
    """
    Fill a Greenhouse application form.
    Returns True if form was successfully filled and left on review/submit page.
    """
    wa = profile.get("work_authorization", {})
    name_parts = profile["name"].split(" ", 1)
    first = name_parts[0]
    last = name_parts[1] if len(name_parts) > 1 else ""

    try:
        fu.fill_field(page, FIELD_MAP["first_name"], first)
        fu.fill_field(page, FIELD_MAP["last_name"], last)
        fu.fill_field(page, FIELD_MAP["email"], profile["email"])
        fu.fill_field(page, FIELD_MAP["phone"], profile["phone"])
        fu.fill_field(page, FIELD_MAP["location"], profile.get("city", profile["location"]))
        fu.fill_field(page, FIELD_MAP["linkedin"], profile.get("linkedin", ""), optional=True)
        fu.fill_field(page, FIELD_MAP["github"], profile.get("github", ""), optional=True)
        fu.fill_field(page, FIELD_MAP["portfolio"], profile.get("portfolio", ""), optional=True)

        fu.upload_resume(page, resume_path, FIELD_MAP["resume"])

        if cover_letter:
            fu.fill_field(page, FIELD_MAP["cover_letter"], cover_letter, optional=True)

        fu.answer_custom_questions(
            page, profile, wa,
            "li.custom-question, div.custom-question, .field",
        )
        return True

    except Exception as e:
        logger.error(f"Greenhouse fill error: {e}")
        return False
