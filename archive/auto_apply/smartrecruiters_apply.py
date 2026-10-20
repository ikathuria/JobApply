"""
SmartRecruiters ATS auto-apply handler (jobs.smartrecruiters.com).

SmartRecruiters renders a single-page application form. Standard fields expose
both ``name``/``id`` attributes and ``data-test`` hooks (e.g.
``data-test="firstName"``). The resume is a standard file input. Screening
questions live in ``.question`` / ``[data-test='question']`` containers.
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
    """Fill a SmartRecruiters application form. Returns True if filled."""
    wa = profile.get("work_authorization", {})
    name_parts = profile.get("name", "").split(" ", 1)
    first = name_parts[0] if name_parts else ""
    last = name_parts[1] if len(name_parts) > 1 else ""

    try:
        fu.fill_field(
            page,
            "input[data-test='firstName'], #firstName, input[name='firstName']",
            first,
        )
        fu.fill_field(
            page,
            "input[data-test='lastName'], #lastName, input[name='lastName']",
            last,
        )
        fu.fill_field(
            page,
            "input[data-test='email'], #email, input[name='email'], input[type='email']",
            profile.get("email", ""),
        )
        fu.fill_field(
            page,
            "input[data-test='phoneNumber'], #phoneNumber, input[name='phoneNumber'], "
            "input[type='tel']",
            profile.get("phone", ""),
            optional=True,
        )
        fu.fill_field(
            page,
            "input[data-test='location'], input[name='location'], "
            "input[placeholder*='ocation']",
            profile.get("city", profile.get("location", "")),
            optional=True,
        )
        fu.fill_field(
            page,
            "input[data-test='linkedinProfileUrl'], input[placeholder*='LinkedIn'], "
            "input[name*='linkedin']",
            profile.get("linkedin", ""),
            optional=True,
        )

        fu.upload_resume(
            page, resume_path,
            "input[type='file'][data-test='resume'], input[type='file']",
        )

        if cover_letter:
            fu.fill_field(
                page,
                "textarea[data-test='coverLetter'], textarea[name*='cover'], "
                "textarea[placeholder*='cover']",
                cover_letter,
                optional=True,
            )

        fu.answer_custom_questions(
            page, profile, wa,
            "[data-test='question'], .question, div[class*='question'], fieldset",
        )
        return True

    except Exception as e:
        logger.error(f"SmartRecruiters fill error: {e}")
        return False
