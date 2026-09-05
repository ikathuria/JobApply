"""
Workday ATS auto-apply handler (*.myworkdayjobs.com).

Workday is deliberately best-effort and *never* fully autonomous:

  * It is a multi-step wizard that requires a per-employer account. Creating
    accounts is out of scope for this tool (it's an action the user must take),
    so if the page is sitting on a sign-in / create-account gate this handler
    stops and tells the user to authenticate manually, then re-run.
  * Once past the gate on the "My Information" step, it fills the standard
    identity/contact/address fields (Workday exposes stable
    ``data-automation-id`` hooks) and attaches the resume, but it does **not**
    click through subsequent steps or submit — the user drives the wizard and
    confirms every submission, as with every other handler.

Returns True if it filled at least the identity fields; False if it hit an auth
gate or couldn't find the form (so the runner flags it for manual completion).
"""

import logging
import time
from pathlib import Path

try:  # Page is used only as a type hint; don't require Playwright to import.
    from playwright.sync_api import Page
except ImportError:  # pragma: no cover
    Page = object  # type: ignore

from auto_apply import form_utils as fu

logger = logging.getLogger(__name__)

# Controls that indicate we're on an auth gate rather than the application form.
_GATE_SELECTORS = [
    "[data-automation-id='createAccountLink']",
    "[data-automation-id='signInLink']",
    "[data-automation-id='createAccountSubmitButton']",
    "[data-automation-id='signInSubmitButton']",
]


def _on_auth_gate(page: Page) -> bool:
    for sel in _GATE_SELECTORS:
        try:
            el = page.query_selector(sel)
        except Exception:
            el = None
        if el and el.is_visible():
            return True
    return False


def apply(page: Page, profile: dict, resume_path: Path, cover_letter: str) -> bool:
    """Fill the Workday 'My Information' step. Returns True if filled."""
    name_parts = profile.get("name", "").split(" ", 1)
    first = name_parts[0] if name_parts else ""
    last = name_parts[1] if len(name_parts) > 1 else ""

    if _on_auth_gate(page):
        logger.warning(
            "Workday requires an account — sign in / create an account in the "
            "browser, advance to the application form, then re-run apply."
        )
        print(
            "     [!] Workday sign-in required. Log in manually in the browser, "
            "reach the 'My Information' step, then re-run --apply for this job."
        )
        return False

    try:
        time.sleep(1)  # Workday renders steps async
        filled = 0
        filled += fu.fill_field(
            page,
            "[data-automation-id='legalNameSection_firstName'], "
            "input[data-automation-id='firstName']",
            first,
        )
        filled += fu.fill_field(
            page,
            "[data-automation-id='legalNameSection_lastName'], "
            "input[data-automation-id='lastName']",
            last,
        )
        fu.fill_field(
            page,
            "[data-automation-id='email'], input[data-automation-id='addressSection_email'], "
            "input[type='email']",
            profile.get("email", ""),
            optional=True,
        )
        fu.fill_field(
            page,
            "[data-automation-id='phone-number'], [data-automation-id='phoneNumber'], "
            "input[type='tel']",
            profile.get("phone", ""),
            optional=True,
        )
        fu.fill_field(
            page,
            "[data-automation-id='addressSection_addressLine1'], "
            "input[data-automation-id='addressLine1']",
            profile.get("address", ""),
            optional=True,
        )
        fu.fill_field(
            page,
            "[data-automation-id='addressSection_city'], input[data-automation-id='city']",
            profile.get("city", ""),
            optional=True,
        )
        fu.fill_field(
            page,
            "[data-automation-id='addressSection_postalCode'], "
            "input[data-automation-id='postalCode']",
            profile.get("zip", ""),
            optional=True,
        )

        fu.upload_resume(
            page, resume_path,
            "input[type='file'][data-automation-id='file-upload-input-ref'], "
            "input[type='file']",
        )

        if filled == 0:
            logger.warning(
                "Workday: identity fields not found — the page may not be on the "
                "'My Information' step. Fill manually in the browser."
            )
            print("     [!] Workday form not detected on this step — fill manually.")
            return False
        return True

    except Exception as e:
        logger.error(f"Workday fill error: {e}")
        return False
