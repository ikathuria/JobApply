"""
JobApply - Orchestrator
Phases:
  1. Discover  - scrape job listings
  2. Filter    - score and store in DB
  3. Tailor    - fetch JD, generate tailored resume + cover letter PDF
  4. Apply     - auto-fill ATS forms with human confirmation before submit

Usage:
  python main.py                          # discover + filter (all sources)
  python main.py --source intern_list     # single source
  python main.py --source linkedin
  python main.py --tailor                 # tailor top unreviewed jobs
  python main.py --tailor --limit 5       # tailor top N jobs
  python main.py --apply                  # apply to approved jobs (you confirm each)
  python main.py --apply --dry-run        # fill forms + screenshot, never submit
  python main.py --apply --limit 5        # apply to top N approved jobs
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

from tracker.tracker import (
    init_db, upsert_jobs, get_jobs, get_stats, update_status,
    STATUS_NEW, STATUS_QUEUED, STATUS_SKIPPED, DB_PATH,
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

    if source in (None, "linkedin") and sources.get("linkedin", {}).get("enabled"):
        from scrapers.linkedin_scraper import scrape_linkedin_sync

        logger.info("=== Scraping LinkedIn ===")
        li_cfg = sources["linkedin"]
        jobs = scrape_linkedin_sync(
            query=li_cfg.get("search_query", "AI ML internship"),
            location="United States",
            easy_apply_only=li_cfg.get("easy_apply_only", True),
            max_jobs=li_cfg.get("max_jobs", 60),
            headless=_CI_HEADLESS,   # headed locally, headless in GHA
        )
        logger.info(f"LinkedIn: {len(jobs)} raw listings")
        all_jobs.extend(jobs)

    if source in (None, "handshake") and sources.get("handshake", {}).get("enabled"):
        from scrapers.handshake_scraper import scrape_handshake_sync

        logger.info("=== Scraping Handshake ===")
        hs_cfg = sources["handshake"]
        jobs = scrape_handshake_sync(
            queries=hs_cfg.get("queries"),
            max_jobs=hs_cfg.get("max_jobs", 80),
            headless=_CI_HEADLESS,   # headed locally, headless in GHA
        )
        logger.info(f"Handshake: {len(jobs)} raw listings")
        all_jobs.extend(jobs)

    return all_jobs


def run_pipeline(config: dict, source: str | None = None) -> None:
    from pipeline.job_filter import filter_jobs, deduplicate

    conn = _open_db()
    min_score = config.get("scoring", {}).get("min_score", 0.3)

    raw_jobs = run_discovery(config, source)
    if not raw_jobs:
        logger.warning("No jobs discovered - check scraper output above.")
        conn.close()
        return

    jobs = deduplicate(raw_jobs)
    filtered = filter_jobs(jobs, min_score=min_score)
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


# -- Phase 2: Tailoring --------------------------------------------------------

def run_tailor(limit: int = 10) -> None:
    """
    For the top-scored unreviewed jobs:
      1. Fetch full JD from URL
      2. Generate tailored resume JSON via LLM
      3. Generate cover letter via LLM
      4. Render both to PDF
      5. Mark job as 'queued' in tracker
    """
    from pipeline.jd_fetcher import fetch_jd
    from pipeline.jobright_enricher import enrich_jobright_url, is_jobright_url
    from pipeline.resume_tailor import tailor_resume
    from pipeline.cover_letter import generate_cover_letter
    from pipeline.pdf_generator import generate_resume_pdf, generate_cover_letter_pdf

    conn = _open_db()
    jobs = get_jobs(conn, status=STATUS_NEW, limit=limit)

    if not jobs:
        print("No new jobs to tailor. Run discovery first.")
        conn.close()
        return

    print(f"\n-- Tailoring {len(jobs)} jobs -------------------------------")

    for job in jobs:
        job = dict(job)
        title_slug = _slug(f"{job['company']}_{job['title']}")
        job_dir = OUTPUT_DIR / title_slug
        job_dir.mkdir(parents=True, exist_ok=True)

        print(f"\n  - {job['title']} @ {job['company'] or 'N/A'}")
        print(f"     Score: {job['score']:.2f} | {job['url']}")

        if is_jobright_url(job.get("source_url") or job.get("url")):
            print("     Enriching Jobright detail page...")
            try:
                source_url = job.get("source_url") or job["url"]
                enriched = enrich_jobright_url(source_url)
                new_status = STATUS_SKIPPED if enriched.is_closed else job["status"]
                update_status(
                    conn,
                    job["id"],
                    new_status,
                    title=enriched.title or job["title"],
                    company=enriched.company or job.get("company"),
                    location=enriched.location or job.get("location"),
                    salary_range=enriched.salary_range or job.get("salary_range"),
                    description=enriched.description or job.get("description"),
                    source_url=source_url,
                    url=enriched.employer_url or job["url"],
                )
                job.update(
                    {
                        "title": enriched.title or job["title"],
                        "company": enriched.company or job.get("company"),
                        "location": enriched.location or job.get("location"),
                        "salary_range": enriched.salary_range or job.get("salary_range"),
                        "description": enriched.description or job.get("description"),
                        "source_url": source_url,
                        "url": enriched.employer_url or job["url"],
                        "status": new_status,
                    }
                )
                if enriched.is_closed:
                    print(f"     [!] Marked skipped: {enriched.closed_reason}")
                    continue
            except Exception as e:
                logger.warning(f"Could not enrich Jobright job {job['id']}: {e}")

        # 1. Fetch JD
        print("     Fetching job description...")
        jd_text = fetch_jd(job["url"])
        if not jd_text:
            logger.warning(f"Could not fetch JD for job {job['id']} - skipping tailoring.")
            print("     [!] Could not fetch JD - skipping.")
            continue

        # Update description in DB
        conn.execute(
            "UPDATE jobs SET description = ?, updated_at = datetime('now') WHERE id = ?",
            (jd_text[:5000], job["id"]),
        )
        conn.commit()

        # 2. Tailor resume
        print("     Generating tailored resume...")
        tailored = tailor_resume(job, jd_text)
        if not tailored:
            print("     [!] Resume tailoring failed - skipping.")
            continue

        # 3. Cover letter
        print("     Generating cover letter...")
        letter_text = generate_cover_letter(job, jd_text, tailored.get("why_fit", ""))

        # 4. Render PDFs
        resume_path = job_dir / "resume.pdf"
        cover_path = job_dir / "cover_letter.pdf"

        generate_resume_pdf(tailored, resume_path)
        if letter_text:
            generate_cover_letter_pdf(letter_text, job, cover_path)
            # Save plain text too for easy editing
            (job_dir / "cover_letter.txt").write_text(letter_text, encoding="utf-8")

        # 5. Mark queued
        update_status(
            conn,
            job["id"],
            STATUS_QUEUED,
            resume_path=str(resume_path),
            notes=f"why_fit: {tailored.get('why_fit', '')}",
        )

        print(f"     - Resume  - {resume_path}")
        if letter_text:
            print(f"     - Cover   - {cover_path}")

    stats = get_stats(conn)
    print("\n-- Updated tracker stats -----------------------")
    for status, count in sorted(stats.items()):
        print(f"  {status:<12} : {count}")
    print()
    conn.close()


def run_enrich_ready(limit: int = 200) -> None:
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from pipeline.jobright_enricher import enrich_jobright_url, is_jobright_url

    conn = _open_db()
    jobs = get_jobs(conn, status=STATUS_QUEUED, limit=limit)
    candidates = []
    for row in jobs:
        job = dict(row)
        source_url = job.get("source_url") or job.get("url") or ""
        if is_jobright_url(source_url):
            candidates.append(job)

    total = 0
    updated = 0
    skipped_closed = 0

    print(f"\n-- Enriching up to {len(candidates)} ready jobs -------------------")

    def _enrich(job: dict) -> tuple[dict, object]:
        source_url = job.get("source_url") or job.get("url") or ""
        return job, enrich_jobright_url(source_url)

    with ThreadPoolExecutor(max_workers=6) as executor:
        future_map = {executor.submit(_enrich, job): job for job in candidates}
        for future in as_completed(future_map):
            job = future_map[future]
            source_url = job.get("source_url") or job.get("url") or ""
            total += 1
            print(f"  - {job['title']} @ {job.get('company') or 'N/A'}")
            try:
                _, enriched = future.result()
            except Exception as e:
                logger.warning(f"Ready-job enrichment failed for {job['id']}: {e}")
                print(f"     [!] enrichment failed: {e}")
                continue

            new_status = STATUS_SKIPPED if enriched.is_closed else job["status"]
            update_status(
                conn,
                job["id"],
                new_status,
                title=enriched.title or job["title"],
                company=enriched.company or job.get("company"),
                location=enriched.location or job.get("location"),
                salary_range=enriched.salary_range or job.get("salary_range"),
                description=enriched.description or job.get("description"),
                source_url=source_url,
                url=enriched.employer_url or job["url"],
            )
            updated += 1
            if enriched.is_closed:
                skipped_closed += 1
                print(f"     skipped: {enriched.closed_reason}")
            else:
                target_url = enriched.employer_url or job["url"]
                print(f"     updated: {target_url}")

    print("\n-- Ready enrichment summary --------------------")
    print(f"  Jobright ready jobs seen : {total}")
    print(f"  Jobs updated            : {updated}")
    print(f"  Marked skipped/closed   : {skipped_closed}")
    print()
    conn.close()


def run_resolve_priority_links(limit: int = 60) -> None:
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from pipeline.jobright_enricher import enrich_jobright_url, is_jobright_url

    conn = _open_db()
    approved = [dict(row) for row in get_jobs(conn, status="approved", limit=limit)]
    ready = [dict(row) for row in get_jobs(conn, status=STATUS_QUEUED, limit=limit)]

    candidates: list[dict] = []
    seen_ids: set[int] = set()
    for bucket in (approved, ready):
        for job in bucket:
            source_url = job.get("source_url") or job.get("url") or ""
            if not is_jobright_url(source_url):
                continue
            if job["id"] in seen_ids:
                continue
            seen_ids.add(job["id"])
            candidates.append(job)

    print(f"\n-- Resolving employer links for {len(candidates)} priority jobs --------")

    updated = 0
    resolved = 0

    def _resolve(job: dict) -> tuple[dict, object]:
        source_url = job.get("source_url") or job.get("url") or ""
        return job, enrich_jobright_url(source_url)

    with ThreadPoolExecutor(max_workers=4) as executor:
        future_map = {executor.submit(_resolve, job): job for job in candidates}
        for future in as_completed(future_map):
            job = future_map[future]
            source_url = job.get("source_url") or job.get("url") or ""
            print(f"  - {job['title']} @ {job.get('company') or 'N/A'}")
            try:
                _, enriched = future.result()
            except Exception as e:
                logger.warning(f"Priority link resolution failed for {job['id']}: {e}")
                print(f"     [!] failed: {e}")
                continue

            target_url = enriched.employer_url or job["url"]
            update_status(
                conn,
                job["id"],
                job["status"],
                source_url=source_url,
                url=target_url,
                salary_range=enriched.salary_range or job.get("salary_range"),
                description=enriched.description or job.get("description"),
                location=enriched.location or job.get("location"),
                company=enriched.company or job.get("company"),
                title=enriched.title or job.get("title"),
            )
            updated += 1
            if target_url != source_url:
                resolved += 1
                print(f"     resolved: {target_url}")
            else:
                print("     still on Jobright URL")

    print("\n-- Priority link summary ------------------------")
    print(f"  Priority jobs checked : {len(candidates)}")
    print(f"  Jobs updated          : {updated}")
    print(f"  Employer URLs found   : {resolved}")
    print()
    conn.close()


# -- Stats ---------------------------------------------------------------------

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


# -- Entry point ---------------------------------------------------------------

def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9_]", "", text.lower().replace(" ", "_"))[:60]


def main() -> None:
    parser = argparse.ArgumentParser(description="JobApply - AI Internship Hunter")
    parser.add_argument("--source", choices=["intern_list", "linkedin", "handshake"])
    parser.add_argument("--tailor", action="store_true", help="Generate tailored resumes for top new jobs")
    parser.add_argument("--apply",   action="store_true", help="Apply to approved jobs (you confirm each submit)")
    parser.add_argument("--dry-run", action="store_true", help="Fill forms + screenshot, never submit")
    parser.add_argument("--limit", type=int, default=10, help="Max jobs to process (default: 10)")
    parser.add_argument("--stats", action="store_true", help="Show tracker stats")
    parser.add_argument("--enrich-ready", action="store_true", help="Refresh ready jobs from Jobright detail pages")
    parser.add_argument("--resolve-priority-links", action="store_true", help="Resolve employer URLs for approved and top ready jobs")
    args = parser.parse_args()

    if args.stats:
        show_stats()
    elif args.enrich_ready:
        run_enrich_ready(limit=args.limit)
    elif args.resolve_priority_links:
        run_resolve_priority_links(limit=args.limit)
    elif args.tailor:
        run_tailor(limit=args.limit)
    elif args.apply:
        from auto_apply.apply_runner import run_apply
        run_apply(limit=args.limit, dry_run=args.dry_run)
    else:
        config = load_config()
        run_pipeline(config, source=args.source)


if __name__ == "__main__":
    main()
