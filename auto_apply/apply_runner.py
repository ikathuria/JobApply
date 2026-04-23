"""
Phase 4: Auto-apply orchestrator.

Modes:
  Local (default)  — headed browser, human confirms before each submit
  Dry-run          — fills form, screenshots result, never submits
  GHA / headless   — headless, auto-submits approved jobs, no human prompt

Run via:
  python main.py --apply [--limit N]           # local, human confirms
  python main.py --apply --dry-run [--limit N] # fill + screenshot, no submit
  python main.py --apply --headless [--limit N] # GHA mode, auto-submit
"""

import json
import logging
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright, Page

from tracker.tracker import (
    init_db, get_jobs, update_status,
    STATUS_QUEUED, STATUS_APPROVED, STATUS_APPLIED, STATUS_SKIPPED,
)

load_dotenv()
logger = logging.getLogger(__name__)

ROOT = Path(__file__).parent.parent


def _get_db():
    """Return a DB connection — Turso when available, local SQLite otherwise."""
    if os.environ.get("TURSO_DATABASE_URL"):
        from api.turso import connect as turso_connect
        from tracker.tracker import _create_tables
        conn = turso_connect()
        _create_tables(conn)
        return conn
    return init_db()

PROFILE_PATH   = Path("config/profile.json")
SCREENSHOT_DIR = Path("output/apply_screenshots")

ATS_PATTERNS = {
    "greenhouse.io":        "greenhouse",
    "boards.greenhouse.io": "greenhouse",
    "grnh.se":              "greenhouse",
    "lever.co":             "lever",
    "jobs.lever.co":        "lever",
    "linkedin.com":         "linkedin",
}


def _load_profile() -> dict:
    with open(PROFILE_PATH) as f:
        return json.load(f)


def _detect_ats(url: str) -> str:
    for pattern, ats in ATS_PATTERNS.items():
        if pattern in url:
            return ats
    return "unknown"


def _find_resume(job: dict) -> Path | None:
    """Resolve resume PDF regardless of which machine generated it."""
    raw = job.get("resume_path")
    if not raw:
        return None
    stored = Path(raw.replace("\\", "/"))
    candidates = [stored]
    if not stored.is_absolute():
        candidates.append(ROOT / stored)
    # Extract portable suffix from 'output/resumes/...' onward
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
    path = job.get("resume_path")
    if not path:
        return ""
    cl = Path(path).parent / "cover_letter.txt"
    return cl.read_text(encoding="utf-8").strip() if cl.exists() else ""


def _confirm(job: dict) -> str:
    """Interactive prompt — returns 'apply', 'skip', or 'quit'."""
    print(f"\n{'='*62}")
    print(f"  📋  {job['title']} @ {job['company']}")
    print(f"  🔗  {job['url'][:70]}")
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
        if sys.stdin.isatty():
            print("\n  [!] LinkedIn 2FA — complete in browser, then press Enter.")
            input("  > ")
        else:
            raise RuntimeError("LinkedIn 2FA required but running non-interactively.")


def _submit_form(page: Page, ats: str) -> bool:
    """Click submit button. Returns True if button found and clicked."""
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


def run_apply(limit: int = 10, dry_run: bool = False, headless: bool = False) -> None:
    """
    Main entry point.
    - dry_run=True  : fill forms + screenshot, never submit
    - headless=True : headless browser, auto-submit approved jobs (GHA mode)
    - default       : headed browser, human confirms each submit
    """
    profile = _load_profile()
    conn    = _get_db()

    # Headless GHA mode picks up 'approved' jobs; local modes use 'queued'
    target_status = STATUS_APPROVED if headless else STATUS_QUEUED
    jobs = get_jobs(conn, status=target_status, limit=limit)

    if not jobs:
        label = "approved" if headless else "queued"
        print(f"No {label} jobs to apply to.")
        if headless:
            print("  Approve jobs via the web dashboard first.")
        else:
            print("  Run --tailor first.")
        conn.close()
        return

    mode_label = "DRY RUN" if dry_run else ("HEADLESS / AUTO-SUBMIT" if headless else "INTERACTIVE")
    print(f"\n-- Auto-Apply [{mode_label}]: {len(jobs)} jobs --------------------")
    if dry_run:
        print("  Forms will be filled and screenshotted. Nothing will be submitted.")
    elif headless:
        print("  Running headlessly. Auto-submitting approved jobs.")
    else:
        print("  Headed browser. You confirm before every submission.")
    print()

    linkedin_logged_in = False
    applied = skipped = errors = 0

    launch_opts = {"headless": headless, "slow_mo": 0 if headless else 80}

    with sync_playwright() as pw:
        browser = pw.chromium.launch(**launch_opts)
        context  = browser.new_context()
        page     = context.new_page()

        for job in jobs:
            job   = dict(job)
            title = job["title"]
            company = job.get("company") or "N/A"
            url   = job["url"]

            resume_path  = _find_resume(job)
            cover_letter = _load_cover_letter(job)

            if not resume_path:
                print(f"  [!] No resume for '{title}' — skipping (run --tailor first)")
                skipped += 1
                continue

            print(f"\n  → {title} @ {company}")

            # Navigate
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=30_000)
                time.sleep(2 if headless else 3)
            except Exception as e:
                print(f"  [!] Navigation failed: {e}")
                errors += 1
                continue

            final_url = page.url
            ats = _detect_ats(final_url)
            print(f"     ATS: {ats} | {final_url[:72]}")

            # Fill form
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

                else:
                    print(f"     [!] Unknown ATS — {'skipping in headless mode' if headless else 'manual fill needed'}")
                    if headless:
                        skipped += 1
                        continue
                    filled = True  # let user fill manually

            except Exception as e:
                logger.error(f"Form fill error for {url}: {e}")
                print(f"     [!] Fill error: {e}")
                errors += 1
                continue

            # Screenshot always
            shot = _take_screenshot(page, job)
            print(f"     Screenshot: {shot}")

            # --- DRY RUN: stop here ---
            if dry_run:
                print(f"     [DRY RUN] Would submit — skipping.")
                continue

            # --- HEADLESS: auto-submit ---
            if headless:
                if not filled:
                    print(f"     [!] Form not filled — skipping.")
                    skipped += 1
                    continue
                submitted = _submit_form(page, ats)
                if submitted:
                    update_status(conn, job["id"], STATUS_APPLIED)
                    print(f"     ✓ Submitted.")
                    applied += 1
                else:
                    print(f"     [!] Submit button not found — skipping.")
                    errors += 1
                time.sleep(1)
                continue

            # --- INTERACTIVE: human confirms ---
            if not filled:
                print(f"     [!] Form fill incomplete — check browser.")

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
                update_status(conn, job["id"], STATUS_APPLIED)
                print(f"     ✓ Applied.")
                applied += 1
            else:
                print(f"     [!] Submit button not found.")
                ans = input("     Mark as applied anyway? [y/n] > ").strip().lower()
                if ans == "y":
                    update_status(conn, job["id"], STATUS_APPLIED)
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
