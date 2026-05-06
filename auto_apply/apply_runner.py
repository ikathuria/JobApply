"""
Phase 4: Interactive apply.

Modes:
  default  — headed browser, fills form, you confirm before each submit
  dry-run  — fills form + screenshot, never submits (good for testing)

Run via:
  python main.py --apply [--limit N]           # fill + confirm each submit
  python main.py --apply --dry-run [--limit N] # fill + screenshot, no submit
"""

import json
import logging
import os
import sys
import time
from datetime import date
from pathlib import Path

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright, Page

from tracker.tracker import (
    init_db, get_jobs, update_status,
    STATUS_APPROVED, STATUS_APPLIED, STATUS_SKIPPED,
)

load_dotenv()
logger = logging.getLogger(__name__)

ROOT = Path(__file__).parent.parent

PROFILE_PATH   = Path("config/profile.json")
SCREENSHOT_DIR = Path("output/apply_screenshots")

ATS_PATTERNS = {
    # Greenhouse
    "greenhouse.io":          "greenhouse",
    "boards.greenhouse.io":   "greenhouse",
    "grnh.se":                "greenhouse",
    # Lever
    "lever.co":               "lever",
    "jobs.lever.co":          "lever",
    # LinkedIn Easy Apply
    "linkedin.com":           "linkedin",
    # Known but unsupported — logged + user fills manually
    "myworkdayjobs.com":      "workday",
    "wd1.myworkdayjobs.com":  "workday",
    "wd3.myworkdayjobs.com":  "workday",
    "ashbyhq.com":            "ashby",
    "jobs.ashbyhq.com":       "ashby",
    "smartrecruiters.com":    "smartrecruiters",
    "jobs.smartrecruiters.com": "smartrecruiters",
    "icims.com":              "icims",
    "taleo.net":              "taleo",
    "jobvite.com":            "jobvite",
    "rippling.com":           "rippling",
}

UNSUPPORTED_ATS = {"workday", "ashby", "smartrecruiters", "icims", "taleo", "jobvite", "rippling"}


def _get_db():
    if os.environ.get("TURSO_DATABASE_URL"):
        from api.turso import connect as turso_connect
        from tracker.tracker import _create_tables
        conn = turso_connect()
        _create_tables(conn)
        return conn
    return init_db()


def _load_profile() -> dict:
    with open(PROFILE_PATH) as f:
        return json.load(f)


def _detect_ats(url: str) -> str:
    for pattern, ats in ATS_PATTERNS.items():
        if pattern in url:
            return ats
    return "unknown"


def _find_resume(job: dict) -> Path | None:
    raw = job.get("resume_path")
    if not raw:
        return None
    stored = Path(raw.replace("\\", "/"))
    candidates = [stored]
    if not stored.is_absolute():
        candidates.append(ROOT / stored)
    parts = stored.parts
    for i, part in enumerate(parts):
        if part in ("output", "resumes"):
            candidates.append(ROOT / Path(*parts[i:]))
            break
    if len(parts) >= 2:
        candidates.append(ROOT / "output" / "resumes" / Path(*parts[-2:]))
    for p in candidates:
        if p.exists():
            return p
    return None


def _load_cover_letter(job: dict) -> str:
    resume_path = _find_resume(job)
    if not resume_path:
        return ""
    cl = resume_path.parent / "cover_letter.txt"
    return cl.read_text(encoding="utf-8").strip() if cl.exists() else ""


def _confirm(job: dict) -> str:
    """Interactive prompt — returns 'apply', 'skip', or 'quit'."""
    print(f"\n{'='*62}")
    print(f"  {job['title']} @ {job['company']}")
    print(f"  {job['url'][:70]}")
    print(f"{'='*62}")
    print("  Review the filled form in the browser.")
    print("  [Enter] Submit  |  [s] Skip  |  [q] Quit")
    choice = input("  > ").strip().lower()
    if choice == "q":
        return "quit"
    if choice == "s":
        return "skip"
    return "apply"


def _take_screenshot(page: Page, job: dict) -> Path:
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    slug = "".join(c if c.isalnum() else "_" for c in
                   f"{job.get('company', '')}_{job['title']}")[:50]
    path = SCREENSHOT_DIR / f"{slug}.png"
    page.screenshot(path=str(path), full_page=True)
    return path


def _linkedin_login(page: Page) -> None:
    email    = os.getenv("LINKEDIN_EMAIL", "")
    password = os.getenv("LINKEDIN_PASSWORD", "")
    if not email or not password:
        raise RuntimeError("LINKEDIN_EMAIL / LINKEDIN_PASSWORD not set in .env")
    page.goto("https://www.linkedin.com/login")
    page.fill("#username", email)
    page.fill("#password", password)
    page.click("button[type='submit']")
    time.sleep(3)
    if "checkpoint" in page.url or "challenge" in page.url:
        print("\n  [!] LinkedIn 2FA — complete in browser, then press Enter.")
        input("  > ")


def _submit_form(page: Page, ats: str) -> bool:
    selectors = {
        "linkedin":   ["button[aria-label='Submit application']"],
        "greenhouse": ["#submit_app", "button[type='submit']", "input[type='submit']"],
        "lever":      ["button[data-qa='btn-submit']", "button[type='submit']"],
    }
    for sel in selectors.get(ats, ["button[type='submit']", "input[type='submit']"]):
        btn = page.query_selector(sel)
        if btn and btn.is_visible():
            btn.click()
            time.sleep(2)
            return True
    return False


def run_apply(limit: int = 10, dry_run: bool = False) -> None:
    """
    Interactive apply runner.
    - dry_run=True : fill form + screenshot, never submit (for testing)
    - default      : fill form, you confirm before each submit
    """
    profile = _load_profile()
    conn    = _get_db()

    jobs = get_jobs(conn, status=STATUS_APPROVED, limit=limit)

    if not jobs:
        print("No approved jobs to apply to.")
        print("  Approve jobs in the dashboard first.")
        conn.close()
        return

    mode_label = "DRY RUN" if dry_run else "INTERACTIVE"
    print(f"\n-- Apply [{mode_label}]: {len(jobs)} approved job{'s' if len(jobs) != 1 else ''} --------------------")
    if dry_run:
        print("  Forms will be filled and screenshotted. Nothing will be submitted.")
    else:
        print("  Headed browser. You confirm before every submission.")
    print()

    linkedin_logged_in = False
    applied = skipped = errors = 0

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=False, slow_mo=80)
        context = browser.new_context()
        page    = context.new_page()

        for job in jobs:
            job     = dict(job)
            title   = job["title"]
            company = job.get("company") or "N/A"
            url     = job["url"]

            resume_path  = _find_resume(job)
            cover_letter = _load_cover_letter(job)

            if not resume_path:
                print(f"  [!] No resume for '{title}' — skipping (run --tailor first)")
                skipped += 1
                continue

            print(f"\n  → {title} @ {company}")

            try:
                page.goto(url, wait_until="domcontentloaded", timeout=30_000)
                time.sleep(3)
            except Exception as e:
                print(f"  [!] Navigation failed: {e}")
                errors += 1
                continue

            final_url = page.url
            ats = _detect_ats(final_url)
            print(f"     ATS: {ats} | {final_url[:72]}")

            filled = False
            try:
                if ats == "linkedin":
                    if not linkedin_logged_in:
                        _linkedin_login(page)
                        linkedin_logged_in = True
                        page.goto(url, wait_until="domcontentloaded", timeout=30_000)
                        time.sleep(2)
                    from auto_apply.linkedin_apply import apply as li_apply
                    filled = li_apply(page, profile, resume_path, cover_letter)

                elif ats == "greenhouse":
                    from auto_apply.greenhouse_apply import apply as gh_apply
                    filled = gh_apply(page, profile, resume_path, cover_letter)

                elif ats == "lever":
                    from auto_apply.lever_apply import apply as lv_apply
                    filled = lv_apply(page, profile, resume_path, cover_letter)

                elif ats in UNSUPPORTED_ATS:
                    print(f"     [!] {ats.capitalize()} ATS — no automated handler. Fill manually in the browser.")
                    filled = True

                else:
                    print(f"     [!] Unrecognized ATS — fill manually in the browser.")
                    filled = True

            except Exception as e:
                logger.error(f"Form fill error for {url}: {e}")
                print(f"     [!] Fill error: {e}")
                errors += 1
                continue

            shot = _take_screenshot(page, job)
            print(f"     Screenshot: {shot}")

            if dry_run:
                print(f"     [DRY RUN] Would submit — skipping.")
                continue

            if not filled:
                print(f"     [!] Form fill incomplete — check browser and fill any missing fields.")

            decision = _confirm(job)
            if decision == "quit":
                print("\n  Stopping.")
                break
            elif decision == "skip":
                update_status(conn, job["id"], STATUS_SKIPPED)
                print(f"     Skipped.")
                skipped += 1
                continue

            submitted = _submit_form(page, ats)
            if submitted:
                update_status(conn, job["id"], STATUS_APPLIED, date_applied=str(date.today()))
                print(f"     Applied.")
                applied += 1
            else:
                print(f"     [!] Submit button not found.")
                ans = input("     Mark as applied anyway? [y/n] > ").strip().lower()
                if ans == "y":
                    update_status(conn, job["id"], STATUS_APPLIED, date_applied=str(date.today()))
                    applied += 1

        browser.close()

    print(f"\n-- Apply run complete ---------------------------------")
    print(f"  Applied  : {applied}")
    print(f"  Skipped  : {skipped}")
    print(f"  Errors   : {errors}")
    if dry_run:
        print(f"  Screenshots in: {SCREENSHOT_DIR}/")
    print()
    conn.close()
