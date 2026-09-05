"""
Lever ATS auto-apply handler.
"""

import logging
from pathlib import Path

try:  # Page is used only as a type hint; don't require Playwright to import.
    from playwright.sync_api import Page
except ImportError:  # pragma: no cover
    Page = object  # type: ignore

from auto_apply import form_utils as fu

logger = logging.getLogger(__name__)


def apply(page: Page, profile: dict, resume_path: Path, cover_letter: str) -> bool:
    """
    Fill a Lever application form.
    Returns True if filled successfully.
    """
    wa = profile.get("work_authorization", {})

    try:
        fu.fill_field(page, "[data-qa='name-field'] input, input[name='name']", profile["name"])
        fu.fill_field(page, "[data-qa='email-field'] input, input[name='email']", profile["email"])
        fu.fill_field(page, "[data-qa='phone-field'] input, input[name='phone']", profile["phone"])
        fu.fill_field(
            page,
            "[data-qa='location-field'] input, input[name='location'], input[placeholder*='ocation']",
            profile.get("city", profile.get("location", "")), optional=True,
        )
        fu.fill_field(
            page,
            "input[name='org'], input[placeholder*='company'], input[placeholder*='Company']",
            profile.get("experience", [{}])[0].get("company", ""), optional=True,
        )
        fu.fill_field(
            page,
            "input[name='urls[LinkedIn]'], input[placeholder*='LinkedIn']",
            profile.get("linkedin", ""), optional=True,
        )
        fu.fill_field(
            page,
            "input[name='urls[GitHub]'], input[placeholder*='GitHub']",
            profile.get("github", ""), optional=True,
        )
        fu.fill_field(
            page,
            "input[name='urls[Portfolio]'], input[placeholder*='portfolio'], input[placeholder*='website']",
            profile.get("portfolio", ""), optional=True,
        )

        fu.upload_resume(page, resume_path, "input[type='file']")

        if cover_letter:
            fu.fill_field(
                page,
                "[data-qa='additional-card'] textarea, textarea[name='comments'], "
                "textarea[placeholder*='cover']",
                cover_letter, optional=True,
            )

        fu.answer_custom_questions(
            page, profile, wa,
            ".application-question, .custom-question, [data-qa='custom-question'], "
            "li[class*='question'], div[class*='question'], "
            ".application-additional-information > div, fieldset",
        )
        return True

    except Exception as e:
        logger.error(f"Lever fill error: {e}")
        return False
