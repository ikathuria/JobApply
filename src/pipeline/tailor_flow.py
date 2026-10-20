"""
The one tailoring flow, shared by ``main.py --tailor`` and the dashboard.

    enrich (Jobright) → JD text → work-auth recheck → tailor (Haiku) → PDF → queued
    later, on demand:  ATS score (Sonnet) → re-tailor if < 90 → PDF refresh
    later, on demand:  cover letter

Each job gets ``output/resumes/<id>_<slug>/`` holding ``resume.pdf`` plus the
inputs the on-demand steps need, so they never refetch or re-tailor from scratch:
``tailored.json`` (resume as data), ``jd.txt``, and ``ats.json`` once scored.
"""

import json
import logging
import re
from pathlib import Path

from pipeline.job_filter import timing_blocker, work_auth_blocker
from tracker.tracker import STATUS_QUEUED, STATUS_SKIPPED, update_status

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = ROOT / "output" / "resumes"
MIN_JD_CHARS = 400  # shorter than this is a snippet, not a JD


class TailorError(Exception):
    """A job couldn't be tailored; ``str(e)`` is user-facing."""


def job_dir(job: dict) -> Path:
    slug = re.sub(r"[^a-z0-9]+", "_", f"{job.get('company') or ''} {job.get('title') or ''}".lower())
    return OUTPUT_DIR / f"{job['id']}_{slug.strip('_')[:50]}"


def _enrich(conn, job: dict) -> dict:
    """Refresh a Jobright job from its detail page; raises TailorError if closed."""
    from pipeline.jobright_enricher import JobrightBlocked, enrich_jobright_url, is_jobright_url

    source_url = job.get("source_url") or job.get("url") or ""
    if not is_jobright_url(source_url):
        return job
    try:
        e = enrich_jobright_url(source_url)
    except JobrightBlocked:
        logger.warning("Jobright rate-limited job %s; using the stored description", job["id"])
        return {**job, "_jobright_blocked": True}
    except Exception as exc:  # network hiccup: tailor from what we have
        logger.warning("Could not enrich job %s: %s", job["id"], exc)
        return job
    if e.is_closed:
        update_status(conn, job["id"], STATUS_SKIPPED, source_url=source_url)
        raise TailorError(f"Job is closed: {e.closed_reason}")
    fields = {
        "title": e.title or job["title"],
        "company": e.company or job.get("company"),
        "location": e.location or job.get("location"),
        "salary_range": e.salary_range or job.get("salary_range"),
        "description": e.description or job.get("description"),
        "source_url": source_url,
        "url": e.employer_url or job["url"],
    }
    update_status(conn, job["id"], job["status"], **fields)
    return {**job, **fields}


def _jd_text(job: dict) -> str:
    """Employer page if it yields a real JD, else the (enriched) stored description."""
    from pipeline.jd_fetcher import fetch_jd

    fetched = ""
    try:
        fetched = fetch_jd(job["url"]) or ""
    except Exception as exc:
        logger.warning("JD fetch failed for job %s: %s", job["id"], exc)
    stored = job.get("description") or ""
    text = fetched if len(fetched) >= len(stored) else stored
    if len(text) < MIN_JD_CHARS:
        if job.get("_jobright_blocked"):
            raise TailorError("Jobright is rate-limiting right now — try again in a few minutes")
        raise TailorError("Could not get a full job description — check the URL")
    return text


def tailor_job(conn, job: dict, cover_letter: bool = False) -> dict:
    """Tailor one job end to end. Returns ``{"message", "resume_path"}``; raises
    TailorError on a user-facing failure (closed, blocked, no JD, LLM failure)."""
    from pipeline.pdf_generator import generate_resume_pdf
    from pipeline.resume_tailor import tailor_resume

    job = _enrich(conn, dict(job))
    jd = _jd_text(job)

    blocker = work_auth_blocker(jd)
    if blocker:
        update_status(conn, job["id"], STATUS_SKIPPED)
        raise TailorError(f"Skipped — work authorization: {blocker!r}")
    early = timing_blocker(f"{job.get('title', '')} {jd}")
    if early:
        update_status(conn, job["id"], STATUS_SKIPPED)
        raise TailorError(f"Skipped — starts before OPT (May 2027): {early!r}")

    tailored = tailor_resume(job, jd)
    if not tailored:
        raise TailorError("Tailoring failed — see logs")
    tailored = _one_page(tailored)

    out = job_dir(job)
    out.mkdir(parents=True, exist_ok=True)
    (out / "jd.txt").write_text(jd, encoding="utf-8")
    (out / "tailored.json").write_text(json.dumps(tailored, indent=1), encoding="utf-8")
    (out / "ats.json").unlink(missing_ok=True)  # a fresh tailor invalidates the old score
    resume_path = out / "resume.pdf"
    generate_resume_pdf(tailored, resume_path)

    if cover_letter:
        write_cover_letter(job, out, jd, tailored)

    update_status(conn, job["id"], STATUS_QUEUED, resume_path=str(resume_path.relative_to(ROOT)),
                  description=jd[:5000], ats_score=None)
    return {"message": f"Tailored for {job.get('company')} ({tailored.get('track', 'ai_ml')} track)",
            "resume_path": str(resume_path.relative_to(ROOT))}


def _one_page(tailored: dict) -> dict:
    from pipeline.pdf_generator import resume_page_count
    from pipeline.resume_tracks import shrink_to_one_page
    return shrink_to_one_page(tailored, resume_page_count)


def _load(job: dict) -> tuple[Path, dict, str]:
    stored = Path(str(job.get("resume_path") or "").replace("\\", "/"))
    out = (stored if stored.is_absolute() else ROOT / stored).parent if job.get("resume_path") else job_dir(job)
    try:
        tailored = json.loads((out / "tailored.json").read_text(encoding="utf-8"))
        jd = (out / "jd.txt").read_text(encoding="utf-8")
    except FileNotFoundError:
        raise TailorError("No tailored resume data for this job — tailor it first")
    return out, tailored, jd


def ats_job(conn, job: dict) -> dict:
    """On-demand ATS check: score with Sonnet, re-tailor below 90, keep the best,
    refresh the PDF if it changed. Returns the stored report."""
    from pipeline.ats_score import ATS_TARGET, ats_check
    from pipeline.pdf_generator import generate_resume_pdf

    out, tailored, jd = _load(job)
    result = ats_check(job, jd, tailored)
    if result["improved"]:
        result["best"] = _one_page(result["best"])
        (out / "tailored.json").write_text(json.dumps(result["best"], indent=1), encoding="utf-8")
        generate_resume_pdf(result["best"], out / "resume.pdf")
    report = {**result["report"], "history": result["history"],
              "improved": result["improved"], "target": ATS_TARGET}
    (out / "ats.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    update_status(conn, job["id"], job["status"], ats_score=report["score"])
    return report


def ats_report(job: dict) -> dict | None:
    """The last stored ATS report for a job, or None."""
    try:
        out, _, _ = _load(job)
        return json.loads((out / "ats.json").read_text(encoding="utf-8"))
    except (TailorError, FileNotFoundError):
        return None


def write_cover_letter(job: dict, out: Path | None = None, jd: str | None = None,
                       tailored: dict | None = None) -> str:
    """Generate (on demand) the cover letter text + PDF for a tailored job."""
    from pipeline.cover_letter import generate_cover_letter
    from pipeline.pdf_generator import generate_cover_letter_pdf

    if out is None or jd is None or tailored is None:
        out, tailored, jd = _load(job)
    text = generate_cover_letter(job, jd, tailored.get("why_fit", ""))
    if not text:
        raise TailorError("Cover letter generation failed — see logs")
    (out / "cover_letter.txt").write_text(text, encoding="utf-8")
    generate_cover_letter_pdf(text, job, out / "cover_letter.pdf")
    return text
