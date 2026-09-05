"""
Ashby ATS auto-apply handler (jobs.ashbyhq.com).

Ashby renders a single-page React application form. System fields carry
``_systemfield_*`` names; the resume is a standard file input. Custom questions
live in ``.ashby-application-form-field-entry`` containers.
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
    """Fill an Ashby application form. Returns True if filled successfully."""
    wa = profile.get("work_authorization", {})
    try:
        fu.fill_field(
            page,
            "input[name='_systemfield_name'], input[name='name'], "
            "input[aria-label='Name'], input[placeholder*='Name']",
            profile.get("name", ""),
        )
        fu.fill_field(
            page,
            "input[name='_systemfield_email'], input[name='email'], "
            "input[type='email'], input[aria-label='Email']",
            profile.get("email", ""),
        )
        fu.fill_field(
            page,
            "input[name='_systemfield_phone'], input[name='phone'], "
            "input[type='tel'], input[aria-label*='Phone']",
            profile.get("phone", ""),
            optional=True,
        )
        fu.fill_field(
            page,
            "input[aria-label*='LinkedIn'], input[placeholder*='LinkedIn']",
            profile.get("linkedin", ""),
            optional=True,
        )
        fu.fill_field(
            page,
            "input[aria-label*='GitHub'], input[placeholder*='GitHub'], "
            "input[placeholder*='github']",
            profile.get("github", ""),
            optional=True,
        )

        fu.upload_resume(page, resume_path, "input[type='file']")

        if cover_letter:
            fu.fill_field(
                page,
                "textarea[aria-label*='Cover'], textarea[placeholder*='cover'], "
                "textarea[name*='cover']",
                cover_letter,
                optional=True,
            )

        fu.answer_custom_questions(
            page, profile, wa,
            ".ashby-application-form-field-entry, "
            "div[class*='_fieldEntry'], fieldset",
        )
        return True

    except Exception as e:
        logger.error(f"Ashby fill error: {e}")
        return False
