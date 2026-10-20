"""
JobApply - Orchestrator
  1. Discover  - scrape job listings (intern-list, newgrad-jobs, Google Careers)
  2. Filter    - score; skip non-sponsors, work-auth blockers, pre-OPT start dates
  3. Tailor    - per job: track resume via the Claude CLI (Haiku) → PDF
  4. Review    - dashboard: optional ATS score (Sonnet), cover letter on demand
  5. Apply     - by hand, then track status in the dashboard

Usage:
  python main.py                          # discover + filter (all enabled sources)
  python main.py --source newgrad_jobs    # single source
  python main.py --tailor --limit 5       # tailor top N new jobs
  python main.py --base-resumes           # render the 4 untailored track PDFs
  python main.py --recruiters --limit 10  # scrape LinkedIn recruiters for DB companies
  python main.py --stats                  # show tracker stats
"""

import argparse
import logging
import os
import re
import sys
from pathlib import Path

# Fix Windows console encoding so emoji in job titles don't crash print()
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# App packages live under src/ — make them importable whether or not the project
# was installed with `pip install -e .`.
sys.path.insert(0, str(Path(__file__).parent / "src"))

from tracker.tracker import (
    init_db, upsert_jobs, get_jobs, get_stats,
    add_recruiter, recruiter_exists, get_target_companies,
    STATUS_NEW, STATUS_QUEUED, DB_PATH,
)


def _open_db():
    """Return a DB connection — Turso when TURSO_DATABASE_URL is set, SQLite otherwise."""
    if os.environ.get("TURSO_DATABASE_URL"):
        from api.turso import connect as turso_connect, seed_from_sqlite
        from tracker.tracker import _create_tables
        conn = turso_connect()
        _create_tables(conn)
        seed_from_sqlite(conn, DB_PATH)  # no-op when Turso already has rows
        return conn
    return init_db()


try:
    from dotenv import load_dotenv
except ModuleNotFoundError:
    load_dotenv = None

if load_dotenv:
    load_dotenv()

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)
OUTPUT_DIR = Path("output/resumes")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

_log_handlers = [logging.StreamHandler(sys.stdout)]
try:
    _log_handlers.append(logging.FileHandler(LOG_DIR / "jobapply.log", encoding="utf-8"))
except OSError:
    pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    handlers=_log_handlers,
)
logger = logging.getLogger("main")


def load_config() -> dict:
    import yaml

    with open("config/settings.yaml") as f:
        return yaml.safe_load(f)


# -- Phase 1: Discovery --------------------------------------------------------

# In CI (GitHub Actions) there's no display — always run browsers headlessly.
_CI_HEADLESS = bool(os.getenv("CI"))


def run_discovery(config: dict, source: str | None = None) -> list[dict]:
    all_jobs = []
    sources = config.get("sources", {})

    if source in (None, "intern_list") and sources.get("intern_list", {}).get("enabled"):
        from scrapers.intern_list_scraper import scrape_intern_list

        logger.info("=== Scraping intern-list.com ===")
        jobs = scrape_intern_list(max_rows=300)
        logger.info(f"intern-list.com: {len(jobs)} raw listings")
        all_jobs.extend(jobs)

    if source in (None, "newgrad_jobs") and sources.get("newgrad_jobs", {}).get("enabled"):
        from scrapers.newgrad_jobs_scraper import scrape_newgrad_jobs

        logger.info("=== Scraping newgrad-jobs.com ===")
        cfg = sources["newgrad_jobs"]
        jobs = scrape_newgrad_jobs(max_rows=cfg.get("max_per_vertical", 300),
                                   verticals=cfg.get("verticals", ["ml_ai"]))
        logger.info(f"newgrad-jobs.com: {len(jobs)} raw listings")
        all_jobs.extend(jobs)

    if source in (None, "google_careers") and sources.get("google_careers", {}).get("enabled"):
        from scrapers.google_careers import scrape_google_careers

        logger.info("=== Scraping Google Careers ===")
        gc_cfg = sources["google_careers"]
        jobs = scrape_google_careers(
            queries=gc_cfg.get("queries"),
            locations=gc_cfg.get("locations"),
            target_levels=gc_cfg.get("target_levels"),
            max_per_query=gc_cfg.get("max_per_query", 200),
        )
        logger.info(f"Google Careers: {len(jobs)} raw listings")
        all_jobs.extend(jobs)

    return all_jobs


def run_pipeline(config: dict, source: str | None = None) -> None:
    from pipeline.job_filter import filter_jobs, deduplicate

    conn = _open_db()
    min_score = config.get("scoring", {}).get("min_score", 0.3)
    require_sponsor = config.get("filters", {}).get("require_known_sponsor", False)

    raw_jobs = run_discovery(config, source)
    if not raw_jobs:
        logger.warning("No jobs discovered - check scraper output above.")
        conn.close()
        return

    jobs = deduplicate(raw_jobs)
    filtered = filter_jobs(jobs, min_score=min_score, require_sponsor=require_sponsor)
    inserted, skipped = upsert_jobs(conn, filtered)

    stats = get_stats(conn)
    print("\n-- Discovery complete --------------------------")
    print(f"  Raw listings found : {len(raw_jobs)}")
    print(f"  Passed filter      : {len(filtered)}")
    print(f"  New in DB          : {inserted}")
    print(f"  Already known      : {skipped}")
    print("\n-- Database totals -----------------------------")
    for status, count in sorted(stats.items()):
        print(f"  {status:<12} : {count}")

    new_jobs = get_jobs(conn, status=STATUS_NEW, min_score=min_score, limit=10)
    if new_jobs:
        print("\n-- Top new jobs (showing up to 10) -------------")
        for i, job in enumerate(new_jobs, 1):
            print(f"  {i:>2}. [{job['score']:.2f}] {job['title']} @ {job['company'] or 'N/A'}")
            print(f"       {job['url']}")
    print()
    conn.close()


# -- Recruiter discovery -------------------------------------------------------

def _split_name(full: str) -> tuple[str, str]:
    """Split a display name into (first, last). Single-token names get a blank last."""
    parts = (full or "").strip().split()
    if not parts:
        return "", ""
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], parts[-1]


def run_scrape_recruiters(config: dict, limit: int | None = None, guess_emails: bool = False) -> None:
    """Separate scraping job: find recruiters on LinkedIn for the companies in
    your jobs DB, and store them (names/titles/profile URLs). With guess_emails,
    resolve emails login-free from each LinkedIn URL (Prospeo) + the finder
    waterfall; otherwise resolve later via the UI's guess-email action."""
    from scrapers.linkedin_recruiter_scraper import scrape_linkedin_recruiters_sync

    rcfg = config.get("recruiters", {})
    if not rcfg.get("enabled", True):
        print("Recruiter scraping is disabled in config (recruiters.enabled: false).")
        return

    conn = _open_db()
    statuses = tuple(rcfg.get("from_statuses") or ())
    companies = get_target_companies(conn, statuses=statuses or None)
    if not companies:
        # Fall back to every company we know about if no outreach-stage jobs yet.
        companies = get_target_companies(conn)
    cap = limit or rcfg.get("max_companies", 25)
    companies = companies[:cap]

    if not companies:
        print("No target companies found in DB — run discovery first.")
        conn.close()
        return

    print(f"\n-- Scraping recruiters for {len(companies)} companies ----------")
    for c in companies:
        print(f"   - {c}")

    recruiters = scrape_linkedin_recruiters_sync(
        companies=companies,
        titles=rcfg.get("titles"),
        max_per_company=rcfg.get("max_per_company", 8),
        headless=_CI_HEADLESS,   # headed locally, headless in GHA
        pace_seconds=rcfg.get("pace_seconds", 5.0),
    )

    finder = None
    if guess_emails:
        from pipeline.email_finder import guess_emails as finder

    added = 0
    duplicate = 0
    emailed = 0
    for r in recruiters:
        if recruiter_exists(conn, linkedin_url=r.get("linkedin_url"),
                            name=r.get("name"), company=r.get("company")):
            duplicate += 1
            continue

        email = None
        if finder:
            first, last = _split_name(r.get("name", ""))
            try:
                # LinkedIn URL alone resolves login-free via Prospeo; no domain needed.
                guesses = finder(first, last, linkedin_url=r.get("linkedin_url"))
                email = guesses[0] if guesses else None
            except Exception as e:
                logger.warning(f"Email lookup failed for {r.get('name')!r}: {e}")

        try:
            add_recruiter(
                conn,
                name=r["name"],
                email=email,
                company=r.get("company"),
                title=r.get("title"),
                linkedin_url=r.get("linkedin_url"),
                source=r.get("source", "linkedin_people"),
            )
            added += 1
            if email:
                emailed += 1
        except Exception as e:
            # Most likely a UNIQUE-email collision with an existing recruiter.
            logger.warning(f"Could not add recruiter {r.get('name')!r}: {e}")

    print("\n-- Recruiter scraping complete -----------------")
    print(f"  Contacts found   : {len(recruiters)}")
    print(f"  New in DB        : {added}")
    print(f"  Already known    : {duplicate}")
    if guess_emails:
        print(f"  Emails resolved  : {emailed}")
    else:
        print("\n  Next: resolve emails from the UI (Outreach → guess email), or "
              "re-run with --guess-emails (set PROSPEO_API_KEY / HUNTER_API_KEY).")
    print()
    conn.close()


# -- Phase 2: Tailoring --------------------------------------------------------

def run_tailor(limit: int = 10, cover_letter: bool = False) -> None:
    """Tailor the top-scored new jobs (pipeline.tailor_flow): enrich → JD →
    work-auth recheck → tailored resume (Haiku) → PDF → queued. Cover letters and
    the ATS score are on demand from the dashboard, to save usage."""
    from pipeline.tailor_flow import TailorError, tailor_job

    conn = _open_db()
    jobs = get_jobs(conn, status=STATUS_NEW, limit=limit)
    if not jobs:
        print("No new jobs to tailor. Run discovery first.")
        conn.close()
        return

    print(f"\n-- Tailoring {len(jobs)} jobs -------------------------------")
    for job in jobs:
        job = dict(job)
        print(f"\n  - {job['title']} @ {job['company'] or 'N/A'}  (score {job['score']:.2f})")
        try:
            res = tailor_job(conn, job, cover_letter=cover_letter)
            print(f"     {res['message']} → {res['resume_path']}")
        except TailorError as e:
            print(f"     [!] {e}")

    print("\n-- Updated tracker stats -----------------------")
    for status, count in sorted(get_stats(conn).items()):
        print(f"  {status:<12} : {count}")
    print()
    conn.close()


def show_stats() -> None:
    conn = _open_db()
    stats = get_stats(conn)
    total = sum(stats.values())
    print("\n-- Application Tracker Stats -------------------")
    for status, count in sorted(stats.items()):
        print(f"  {status:<12} : {count}")
    print(f"  {'TOTAL':<12} : {total}")

    queued = get_jobs(conn, status=STATUS_QUEUED, limit=5)
    if queued:
        print("\n-- Queued (ready to apply) ---------------------")
        for job in queued:
            print(f"  [{job['score']:.2f}] {job['title']} @ {job['company'] or 'N/A'}")
    conn.close()


def run_scan_inbox(limit: int = 500, ingest: bool = False, days: int = 60) -> None:
    """Read recruiter replies over IMAP and auto-advance job statuses (M20).
    With ingest=True, also reconstruct applications from the 'job apps' folder."""
    from pipeline.inbox_scan import scan_inbox, print_summary
    conn = _open_db()
    try:
        print_summary(scan_inbox(conn, limit=limit, days=days, ingest=ingest))
    finally:
        conn.close()


def run_digest() -> None:
    """Compose + email the weekly digest (M23)."""
    from pipeline.digest import send_digest
    conn = _open_db()
    try:
        ok = send_digest(conn)
        print("Digest sent." if ok else
              "Digest not sent — check SMTP creds / notifications.email_to.")
    finally:
        conn.close()


def run_reminder() -> None:
    """Compose + email the daily apply/referral reminder (M35)."""
    from pipeline.daily_reminder import send_reminder
    conn = _open_db()
    try:
        ok = send_reminder(conn)
        print("Daily reminder sent." if ok else
              "Reminder not sent — check SMTP creds / notifications.email_to.")
    finally:
        conn.close()


def run_dedup() -> None:
    """Detect + skip duplicate NEW listings across sources (M24)."""
    from pipeline.dedup import dedup_new_jobs
    conn = _open_db()
    try:
        groups = dedup_new_jobs(conn)
        skipped = sum(len(g) - 1 for g in groups)
        print(f"\n-- Dedup: {len(groups)} duplicate group(s), skipped {skipped} listing(s) --")
        for g in groups[:15]:
            kept = g[0]
            print(f"  keep [{kept['score']:.2f}] {kept['title']} @ {kept['company']} "
                  f"(+{len(g) - 1} dup)")
        print()
    finally:
        conn.close()


# -- Entry point ---------------------------------------------------------------

def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9_]", "", text.lower().replace(" ", "_"))[:60]


def run_base_resumes() -> None:
    """Render one untailored PDF per resume track (M41) for quick applies."""
    import json
    from pipeline.pdf_generator import generate_resume_pdf
    from pipeline.resume_tracks import base_resume

    profile = json.loads(Path("config/profile.json").read_text())
    out_dir = Path("output/resumes/base")
    out_dir.mkdir(parents=True, exist_ok=True)
    tracks = sorted(profile.get("tracks", {}).items(), key=lambda kv: kv[1].get("priority", 99))
    for track, spec in tracks:
        label = spec.get("label", track).replace("/", "-").replace(" ", "_")
        path = out_dir / f"Ishani_Kathuria_{label}.pdf"
        generate_resume_pdf(base_resume(profile, track), path)
        print(f"  {spec.get('label', track):22s} → {path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="JobApply - AI Internship Hunter")
    parser.add_argument("--source", choices=["intern_list", "newgrad_jobs", "google_careers"])
    parser.add_argument("--tailor", action="store_true", help="Generate tailored resumes for top new jobs")
    parser.add_argument("--recruiters", action="store_true",
                        help="Scrape LinkedIn recruiters for the companies in your jobs DB")
    parser.add_argument("--guess-emails", action="store_true",
                        help="With --recruiters: resolve emails (Prospeo by LinkedIn URL + finder waterfall)")
    parser.add_argument("--limit", type=int, default=10, help="Max jobs to process (default: 10)")
    parser.add_argument("--stats", action="store_true", help="Show tracker stats")
    parser.add_argument("--scan-inbox", action="store_true",
                        help="Read recruiter replies over IMAP and auto-advance job statuses")
    parser.add_argument("--ingest", action="store_true",
                        help="With --scan-inbox: also create tracked applications from the "
                             "'job apps' folder (reconstruct the funnel from email)")
    parser.add_argument("--days", type=int, default=60,
                        help="With --scan-inbox: how many days of mail to read (default: 60)")
    parser.add_argument("--digest", action="store_true",
                        help="Email a weekly summary (new jobs, reviews, follow-ups, windows)")
    parser.add_argument("--remind", action="store_true",
                        help="Email a daily nudge (what to apply to, who to ask for referrals, follow-ups)")
    parser.add_argument("--base-resumes", action="store_true",
                        help="Render the 4 untailored track resumes → output/resumes/base/")
    parser.add_argument("--dedup", action="store_true",
                        help="Detect duplicate NEW listings across sources and skip the extras")
    args = parser.parse_args()

    if args.stats:
        show_stats()
    elif args.recruiters:
        config = load_config()
        run_scrape_recruiters(
            config,
            limit=args.limit if "--limit" in sys.argv else None,
            guess_emails=args.guess_emails,
        )
    elif args.tailor:
        run_tailor(limit=args.limit)
    elif args.scan_inbox:
        run_scan_inbox(limit=args.limit if "--limit" in sys.argv else 500,
                       ingest=args.ingest, days=args.days)
    elif args.digest:
        run_digest()
    elif args.remind:
        run_reminder()
    elif args.dedup:
        run_dedup()
    elif args.base_resumes:
        run_base_resumes()
    else:
        config = load_config()
        run_pipeline(config, source=args.source)


if __name__ == "__main__":
    main()
