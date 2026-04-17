"""
Phase 4: Auto-apply orchestrator.

For each queued job:
  1. Open the job URL in a visible browser
  2. Detect the ATS (Greenhouse, Lever, LinkedIn, or unknown)
  3. Fill the form with profile data + tailored resume/cover letter
  4. Pause for human review — user presses Enter to submit or 's' to skip
  5. Submit and mark as 'applied' in the tracker

Run via:  python main.py --apply [--limit N]
"""

import json
import logging
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright, Page

from tracker.tracker import init_db, get_jobs, update_status, STATUS_QUEUED, STATUS_APPLIED, STATUS_SKIPPED

load_dotenv()
logger = logging.getLogger(__name__)

PROFILE_PATH = Path("config/profile.json")

ATS_PATTERNS = {
    "greenhouse.io":       "greenhouse",
    "boards.greenhouse.io": "greenhouse",
    "grnh.se":             "greenhouse",
    "lever.co":            "lever",
    "jobs.lever.co":       "lever",
    "linkedin.com":        "linkedin",
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
    resume_path = job.get("resume_path")
    if resume_path and Path(resume_path).exists():
        return Path(resume_path)
    return None


def _load_cover_letter(job: dict) -> str:
    resume_path = job.get("resume_path")
    if not resume_path:
        return ""
    cl_txt = Path(resume_path).parent / "cover_letter.txt"
    if cl_txt.exists():
        return cl_txt.read_text(encoding="utf-8").strip()
    return ""


def _confirm(job: dict) -> str:
    """
    Ask user to confirm before submitting.
    Returns 'apply', 'skip', or 'quit'.
    """
    print(f"\n{'='*60}")
    print(f"  Ready to submit: {job['title']} @ {job['company']}")
    print(f"  URL: {job['url']}")
    print(f"{'='*60}")
    print("  Review the form in the browser window.")
    print("  [Enter] Submit  |  [s] Skip  |  [q] Quit")
    choice = input("  > ").strip().lower()
    if choice == "q":
        return "quit"
    if choice == "s":
        return "skip"
    return "apply"


def _linkedin_login(page: Page) -> None:
    email = os.getenv("LINKEDIN_EMAIL", "")
    password = os.getenv("LINKEDIN_PASSWORD", "")
    if not email or not password:
        raise RuntimeError("LINKEDIN_EMAIL / LINKEDIN_PASSWORD not set in .env")

    page.goto("https://www.linkedin.com/login")
    page.fill("#username", email)
    page.fill("#password", password)
    page.click("button[type='submit']")
    time.sleep(3)

    if "checkpoint" in page.url or "challenge" in page.url:
        print("\n  [!] LinkedIn 2FA required — complete it in the browser, then press Enter.")
        input("  Press Enter when done > ")


def run_apply(limit: int = 10) -> None:
    profile = _load_profile()
    conn = init_db()
    jobs = get_jobs(conn, status=STATUS_QUEUED, limit=limit)

    if not jobs:
        print("No queued jobs to apply to. Run --tailor first.")
        conn.close()
        return

    print(f"\n-- Auto-Apply: {len(jobs)} queued jobs ------------------")
    print("  Browser will open for each application.")
    print("  You confirm before every submission.\n")

    linkedin_logged_in = False
    applied = skipped = 0

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=False, slow_mo=100)
        context = browser.new_context()
        page = context.new_page()

        for job in jobs:
            job = dict(job)
            title = job["title"]
            company = job["company"] or "N/A"
            url = job["url"]

            resume_path = _find_resume(job)
            cover_letter = _load_cover_letter(job)

            if not resume_path:
                logger.warning(f"No resume PDF found for '{title}' — skipping")
                print(f"  [!] No resume for {title} @ {company} — skipping (run --tailor first)")
                continue

            print(f"\n  Applying: {title} @ {company}")

            # Navigate to job URL
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=30_000)
                time.sleep(3)
            except Exception as e:
                logger.error(f"Navigation failed for {url}: {e}")
                print(f"  [!] Could not load page: {e}")
                continue

            final_url = page.url
            ats = _detect_ats(final_url)
            print(f"     ATS detected: {ats} | {final_url[:80]}")

            filled = False

            if ats == "linkedin":
                if not linkedin_logged_in:
                    try:
                        _linkedin_login(page)
                        linkedin_logged_in = True
                        page.goto(url, wait_until="domcontentloaded", timeout=30_000)
                        time.sleep(2)
                    except Exception as e:
                        print(f"  [!] LinkedIn login failed: {e}")
                        continue
                from auto_apply.linkedin_apply import apply as li_apply
                filled = li_apply(page, profile, resume_path, cover_letter)

            elif ats == "greenhouse":
                from auto_apply.greenhouse_apply import apply as gh_apply
                filled = gh_apply(page, profile, resume_path, cover_letter)

            elif ats == "lever":
                from auto_apply.lever_apply import apply as lv_apply
                filled = lv_apply(page, profile, resume_path, cover_letter)

            else:
                print(f"     [!] Unknown ATS — opening browser for manual application.")
                print(f"         Press Enter when done (or 's' to skip, 'q' to quit).")
                filled = True  # Let user fill manually, still ask for confirm

            if not filled:
                print(f"  [!] Form fill failed — opening browser for manual review.")

            # Human confirmation before submit
            decision = _confirm(job)

            if decision == "quit":
                print("\n  Stopping apply run.")
                break
            elif decision == "skip":
                update_status(conn, job["id"], STATUS_SKIPPED)
                print(f"  Skipped: {title} @ {company}")
                skipped += 1
                continue

            # Submit
            submitted = False
            if ats == "linkedin":
                submit_btn = page.query_selector("button[aria-label='Submit application']")
                if submit_btn:
                    submit_btn.click()
                    time.sleep(2)
                    submitted = True
            elif ats in ("greenhouse", "lever"):
                for sel in ["#submit_app", "button[type='submit']", "input[type='submit']",
                            "button[data-qa='btn-submit']"]:
                    btn = page.query_selector(sel)
                    if btn:
                        btn.click()
                        submitted = True
                        break
            else:
                # Unknown ATS — user already submitted manually
                submitted = True

            if submitted:
                update_status(conn, job["id"], STATUS_APPLIED)
                print(f"  Applied: {title} @ {company}")
                applied += 1
                time.sleep(2)
            else:
                print(f"  [!] Submit button not found — mark as applied manually? [y/n]")
                if input("  > ").strip().lower() == "y":
                    update_status(conn, job["id"], STATUS_APPLIED)
                    applied += 1

        browser.close()

    print(f"\n-- Apply run complete ----------------------------------")
    print(f"  Applied : {applied}")
    print(f"  Skipped : {skipped}")
    print()
    conn.close()
