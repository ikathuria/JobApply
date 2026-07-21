"""
FastAPI backend for JobApply — React UI data layer.
Run: uvicorn api.main:app --reload --port 8000
"""

from __future__ import annotations
import hashlib
import json
import logging
import os
import re
import shutil
import sqlite3
import sys
from contextlib import asynccontextmanager
from pathlib import Path

import yaml
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# src/api/main.py → repo root is three levels up (src/api/ → src/ → root)
ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT / "src"))

# Load .env for local dev so LLM/SMTP endpoints work when running uvicorn
# directly. In production (Render) env vars come from the platform and no .env
# exists, so this is a harmless no-op there.
try:
    from dotenv import load_dotenv
    load_dotenv()
except ModuleNotFoundError:
    pass

from tracker.tracker import (
    init_db, get_jobs, get_stats, update_status,
    STATUS_NEW, STATUS_QUEUED, STATUS_APPROVED, STATUS_APPLIED,
    STATUS_OA, STATUS_INTERVIEW, STATUS_REJECTED, STATUS_OFFER, STATUS_SKIPPED,
    add_recruiter, get_recruiter, get_recruiter_by_email, list_recruiters,
    update_recruiter, delete_recruiter,
    add_outreach, get_outreach, list_outreach_for_recruiter, update_outreach,
    update_outreach_status, list_followups_due,
    OUTREACH_COLD, OUTREACH_REFERRAL, OUTREACH_SENT,
    add_reminder, get_reminder, list_reminders, list_reminders_due,
    update_reminder, delete_reminder, REMINDER_APPLY,
    upsert_prep, get_prep, delete_prep, list_prep_jobs,
)

# Use uvicorn's configured logger so startup lines actually appear in its output
# (a bare app logger doesn't propagate to uvicorn's handlers).
logger = logging.getLogger("uvicorn.error")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Log the DB backend + committed PDF count on startup (M11)."""
    backend = "turso" if os.environ.get("TURSO_DATABASE_URL") else "sqlite"
    out_dir = Path(os.environ.get("OUTPUT_DIR", str(ROOT / "output" / "resumes")))
    pdfs = len(list(out_dir.rglob("resume.pdf"))) if out_dir.exists() else 0
    dist = (ROOT / "apps" / "web" / "dist").exists()
    logger.info(f"JobApply API up — db={backend}, resume PDFs={pdfs}, web dist={'yes' if dist else 'no'}")
    yield


app = FastAPI(title="JobApply API", version="2.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# In production (Render), DB_PATH env var points to the persistent disk.
# Locally it falls back to tracker/applications.db in the repo.
_db_env = os.environ.get("DB_PATH")
DB_PATH = Path(_db_env) if _db_env else ROOT / "src" / "tracker" / "applications.db"

# Seed the persistent-disk DB from the repo copy on first deploy
_git_db = ROOT / "src" / "tracker" / "applications.db"
if _db_env and not DB_PATH.exists() and _git_db.exists():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(_git_db, DB_PATH)

OUTPUT_DIR = Path(os.environ.get("OUTPUT_DIR", str(ROOT / "output" / "resumes")))

# ── Singleton DB connection ───────────────────────────────────────────────────
# Uses Turso (libsql) when TURSO_DATABASE_URL is set, sqlite3 otherwise.

_conn = None


_GIT_DB = ROOT / "src" / "tracker" / "applications.db"   # always the git-committed copy


def db():
    global _conn
    if _conn is None:
        if os.environ.get("TURSO_DATABASE_URL"):
            import threading
            from api.turso import connect as turso_connect, seed_from_sqlite
            from tracker.tracker import _create_tables  # type: ignore[attr-defined]
            _conn = turso_connect()
            _create_tables(_conn)            # schema first (fast, ~5 HTTP calls)
            # Seed in background — app responds immediately, jobs appear within seconds
            threading.Thread(
                target=seed_from_sqlite, args=(_conn, _GIT_DB), daemon=True
            ).start()
        else:
            _conn = init_db(DB_PATH)         # local: plain sqlite3
    return _conn


# ── Health ────────────────────────────────────────────────────────────────────


@app.get("/api/health")
def api_health() -> dict:
    """Lightweight liveness + backend probe for Render health checks (M11)."""
    backend = "turso" if os.environ.get("TURSO_DATABASE_URL") else "sqlite"
    jobs = None
    try:
        jobs = db().execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
    except Exception:
        pass
    return {"status": "ok", "db": backend, "jobs": jobs}


# ── Stats ─────────────────────────────────────────────────────────────────────


@app.get("/api/stats")
def api_stats() -> dict:
    conn = db()
    s = get_stats(conn)

    # Breakdown of rejected jobs by which stage they were rejected at
    stage_rows = conn.execute(
        "SELECT COALESCE(rejection_stage, 'Unknown') as stage, COUNT(*) as cnt "
        "FROM jobs WHERE status = 'rejected' GROUP BY rejection_stage "
        "ORDER BY cnt DESC"
    ).fetchall()
    rejection_stages = {row["stage"]: row["cnt"] for row in stage_rows}

    applied_n   = s.get(STATUS_APPLIED,   0)
    oa_n        = s.get(STATUS_OA,        0)
    interview_n = s.get(STATUS_INTERVIEW, 0)
    offer_n     = s.get(STATUS_OFFER,     0)
    rejected_n  = s.get(STATUS_REJECTED,  0)

    # total_applied = everyone who actually submitted an application
    # (jobs that progressed past "applied" status also count as applied)
    total_applied = applied_n + oa_n + interview_n + offer_n + rejected_n

    return {
        "total":         sum(s.values()),
        "new":           s.get(STATUS_NEW,       0),
        "ready":         s.get(STATUS_QUEUED,    0),
        "approved":      s.get(STATUS_APPROVED,  0),
        "applied":       applied_n,
        "total_applied": total_applied,
        "oa":            oa_n,
        "interview":     interview_n,
        "offer":         offer_n,
        "rejected":      rejected_n,
        "skipped":       s.get(STATUS_SKIPPED,   0),
        "rejection_stages": rejection_stages,
    }


# ── Focus items ───────────────────────────────────────────────────────────────


@app.get("/api/focus")
def api_focus() -> list[dict]:
    conn = db()
    stats = get_stats(conn)
    items: list[dict] = []

    n_ready = stats.get(STATUS_QUEUED, 0)
    if n_ready:
        items.append({
            "id": "f_ready", "type": "tailor",
            "icon": "✦", "color": "#22C55E",
            "label": f"{n_ready} job{'s' if n_ready != 1 else ''} tailored and ready to review",
            "cta": "Review Ready", "tab": "ready", "jobId": None,
        })

    # Highlight top approved job waiting for submission
    approved_job = conn.execute(
        "SELECT * FROM jobs WHERE status=? ORDER BY score DESC LIMIT 1", (STATUS_APPROVED,)
    ).fetchone()
    if approved_job:
        j = dict(approved_job)
        items.append({
            "id": "f_approve", "type": "confirm",
            "icon": "⚡", "color": "#8B5CF6",
            "label": f"{j['company']} is approved — ready to submit",
            "cta": "Submit Application", "tab": "approved", "jobId": j["id"],
        })
    elif stats.get(STATUS_QUEUED, 0):
        # Fall back to top queued job awaiting approval
        ready_job = conn.execute(
            "SELECT * FROM jobs WHERE status=? ORDER BY score DESC LIMIT 1", (STATUS_QUEUED,)
        ).fetchone()
        if ready_job:
            j = dict(ready_job)
            items.append({
                "id": "f_approve", "type": "confirm",
                "icon": "✓", "color": "#8B5CF6",
                "label": f"{j['company']} application awaits your approval",
                "cta": "Review & Approve", "tab": "ready", "jobId": j["id"],
            })

    oa_job = conn.execute(
        "SELECT * FROM jobs WHERE status=? ORDER BY date_applied DESC LIMIT 1", (STATUS_OA,)
    ).fetchone()
    if oa_job:
        j = dict(oa_job)
        items.append({
            "id": "f_oa", "type": "oa",
            "icon": "📝", "color": "#F59E0B",
            "label": f"{j['company']} sent an online assessment",
            "cta": "View Job", "tab": "applied", "jobId": j["id"],
        })

    int_job = conn.execute(
        "SELECT * FROM jobs WHERE status=? ORDER BY interview_date ASC LIMIT 1", (STATUS_INTERVIEW,)
    ).fetchone()
    if int_job:
        j = dict(int_job)
        date_str = (j.get("interview_date") or "")[:10] or "soon"
        items.append({
            "id": "f_interview", "type": "interview",
            "icon": "🎤", "color": "#EC4899",
            "label": f"{j['company']} interview on {date_str} — prep time!",
            "cta": "View Details", "tab": "applied", "jobId": j["id"],
        })

    return items


# ── Jobs list ─────────────────────────────────────────────────────────────────


@app.get("/api/jobs")
def api_jobs(
    status: str | None = None,
    search: str = "",
    min_score: float = 0.0,
    sort: str = "score",
    page: int = 0,
    limit: int = 100,
) -> dict:
    rows = get_jobs(db(), status=status or None, min_score=min_score, limit=2000)
    jobs = [dict(r) for r in rows]

    if search:
        q = search.lower()
        jobs = [
            j for j in jobs
            if q in (j.get("title")    or "").lower()
            or q in (j.get("company")  or "").lower()
            or q in (j.get("location") or "").lower()
        ]

    if sort == "company":
        jobs.sort(key=lambda j: (j.get("company") or "").lower())
    elif sort == "starred":
        jobs.sort(key=lambda j: (j.get("score") or 0), reverse=True)
    else:
        jobs.sort(key=lambda j: (j.get("score") or 0), reverse=True)

    # Starred always float to top
    jobs = [j for j in jobs if j.get("starred")] + [j for j in jobs if not j.get("starred")]

    total = len(jobs)
    start = page * limit
    return {"jobs": jobs[start : start + limit], "total": total, "page": page}


# ── Single job ────────────────────────────────────────────────────────────────


@app.get("/api/jobs/{job_id}")
def api_get_job(job_id: int) -> dict:
    row = db().execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Job not found")
    return dict(row)


# ── Patch job ─────────────────────────────────────────────────────────────────


class JobPatch(BaseModel):
    status: str | None = None
    notes: str | None = None
    starred: int | None = None
    date_applied: str | None = None
    recruiter: str | None = None
    salary_range: str | None = None
    interview_date: str | None = None
    follow_up_date: str | None = None
    rejection_stage: str | None = None
    score: float | None = None
    title: str | None = None
    company: str | None = None
    location: str | None = None
    url: str | None = None
    source_url: str | None = None


# Status → the settings toggle that gates a notification email on that transition.
_NOTIFY_STATUS = {"offer": "on_offer", "interview": "on_interview"}


def _maybe_notify_status(job: dict, new_status: str) -> None:
    """Email a notification when a job reaches a milestone status (offer/interview),
    if the matching toggle is on. Reuses the Gmail sender; no-op without creds (M10)."""
    key = _NOTIFY_STATUS.get(new_status)
    if not key:
        return
    notif = _read_settings_file().get("notifications", {})
    if not notif.get(key):
        return
    to = (notif.get("email_to") or os.environ.get("GMAIL_ADDRESS") or "").strip()
    if not to:
        logger.warning("Status notification skipped — set notifications.email_to or GMAIL_ADDRESS")
        return
    company = job.get("company") or "a company"
    title = job.get("title") or "a role"
    subject = f"[JobApply] {company} → {new_status.upper()}: {title}"
    body = (
        f"Status update: {title} @ {company} moved to {new_status.upper()}.\n\n"
        f"URL: {job.get('url', '')}\n"
    )
    try:
        from pipeline.email_sender import send_email
        ok = send_email(to, subject, body)
        logger.info(f"Status notification for job {job.get('id')} → {new_status}: sent={ok}")
    except Exception as e:
        logger.warning(f"Status notification failed: {e}")


@app.patch("/api/jobs/{job_id}")
def api_patch_job(job_id: int, patch: JobPatch) -> dict:
    conn = db()
    row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Job not found")

    current = dict(row)
    new_status = patch.status or current["status"]

    kwargs = patch.model_dump(exclude={"status"}, exclude_unset=True)
    update_status(conn, job_id, new_status, **kwargs)

    updated = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()

    # Notify on a genuine transition into a milestone status (never breaks the patch).
    if patch.status and patch.status != current["status"]:
        try:
            _maybe_notify_status(dict(updated), new_status)
        except Exception as e:
            logger.warning(f"Notification hook error: {e}")

    return dict(updated)


# ── Bulk status update ────────────────────────────────────────────────────────


class BulkPatch(BaseModel):
    ids: list[int]
    status: str


@app.post("/api/jobs/bulk")
def api_bulk_patch(body: BulkPatch) -> dict:
    """Update status for multiple jobs in one call."""
    from datetime import date as _date
    conn = db()
    extra = {}
    if body.status == "applied":
        extra["date_applied"] = str(_date.today())
    for job_id in body.ids:
        update_status(conn, job_id, body.status, **extra)
    return {"updated": len(body.ids), "status": body.status}


# ── Tailor ────────────────────────────────────────────────────────────────────


@app.post("/api/jobs/{job_id}/tailor")
def api_tailor(job_id: int) -> dict:
    conn = db()
    row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Job not found")
    job = dict(row)

    try:
        from pipeline.jd_fetcher import fetch_jd
        from pipeline.jobright_enricher import enrich_jobright_url, is_jobright_url
        from pipeline.resume_tailor import tailor_resume
        from pipeline.cover_letter import generate_cover_letter
        from pipeline.pdf_generator import generate_resume_pdf, generate_cover_letter_pdf

        source_url = job.get("source_url") or job.get("url") or ""
        if is_jobright_url(source_url):
            enriched = enrich_jobright_url(source_url)
            if enriched.is_closed:
                update_status(conn, job_id, STATUS_SKIPPED, source_url=source_url)
                raise HTTPException(400, f"Job is closed: {enriched.closed_reason}")
            update_status(
                conn,
                job_id,
                job["status"],
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
                }
            )

        jd_text = fetch_jd(job["url"])
        if not jd_text:
            raise HTTPException(400, "Could not fetch job description — check URL")

        tailored = tailor_resume(job, jd_text)
        if not tailored:
            raise HTTPException(500, "Tailoring failed — check API key in Streamlit secrets")

        slug = re.sub(r"[^a-z0-9_]", "", f"{job.get('company', '')}{job['title']}".lower().replace(" ", "_"))[:60]
        job_dir = OUTPUT_DIR / slug
        job_dir.mkdir(parents=True, exist_ok=True)
        resume_path = job_dir / "resume.pdf"

        letter_text = generate_cover_letter(job, jd_text, tailored.get("why_fit", ""))
        generate_resume_pdf(tailored, resume_path)

        if letter_text:
            generate_cover_letter_pdf(letter_text, job, job_dir / "cover_letter.pdf")
            (job_dir / "cover_letter.txt").write_text(letter_text, encoding="utf-8")

        update_status(conn, job_id, STATUS_QUEUED, resume_path=str(resume_path))
        return {"status": "ok", "message": f"Tailored for {job.get('company')}"}

    except (ImportError, ModuleNotFoundError) as e:
        raise HTTPException(503, f"Pipeline module unavailable: {e}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


# ── Resume PDF ────────────────────────────────────────────────────────────────


def _resolve_resume_path(raw: str) -> Path | None:
    """
    Find a resume PDF regardless of which machine generated it.

    Tries in order:
    1. The stored path as-is (works locally when path matches)
    2. The stored path relative to ROOT (works when a relative path was stored)
    3. The 'output/resumes/...' suffix relative to ROOT (fixes GHA / cross-machine paths)
    4. Just the filename under ROOT/output/resumes/ (last resort)
    """
    stored = Path(raw.replace("\\", "/"))

    candidates = [stored]
    if not stored.is_absolute():
        candidates.append(ROOT / stored)

    # Extract the portable suffix: everything from 'output/resumes/' onward
    parts = stored.parts
    for i, part in enumerate(parts):
        if part in ("output", "resumes"):
            # Try joining from here to the end
            suffix = Path(*parts[i:])
            candidates.append(ROOT / suffix)
            break

    # Also try just slug/resume.pdf under ROOT/output/resumes/
    if len(parts) >= 2:
        candidates.append(ROOT / "output" / "resumes" / Path(*parts[-2:]))

    for p in candidates:
        if p.exists():
            return p
    return None


@app.get("/api/jobs/{job_id}/resume")
def api_get_resume(job_id: int):
    row = db().execute("SELECT resume_path FROM jobs WHERE id = ?", (job_id,)).fetchone()
    if not row or not row["resume_path"]:
        raise HTTPException(404, "No resume found")
    p = _resolve_resume_path(str(row["resume_path"]))
    if not p:
        raise HTTPException(404, "Resume file not found on disk")
    return FileResponse(str(p), media_type="application/pdf",
                        headers={"Content-Disposition": "inline; filename=resume.pdf"})


# ── Cover letter ──────────────────────────────────────────────────────────────


@app.get("/api/jobs/{job_id}/cover_letter")
def api_get_cover_letter(job_id: int) -> PlainTextResponse:
    row = db().execute("SELECT resume_path FROM jobs WHERE id = ?", (job_id,)).fetchone()
    if not row or not row["resume_path"]:
        raise HTTPException(404, "No resume path")
    resume_p = _resolve_resume_path(str(row["resume_path"]))
    if not resume_p:
        raise HTTPException(404, "Resume directory not found")
    cl_txt = resume_p.parent / "cover_letter.txt"
    if not cl_txt.exists():
        raise HTTPException(404, "Cover letter not found")
    return PlainTextResponse(cl_txt.read_text(encoding="utf-8"))


@app.get("/api/jobs/{job_id}/cover_letter.pdf")
def api_get_cover_letter_pdf(job_id: int):
    row = db().execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    if not row or not row["resume_path"]:
        raise HTTPException(404, "No resume path")
    resume_p = _resolve_resume_path(str(row["resume_path"]))
    if not resume_p:
        raise HTTPException(404, "Resume directory not found")
    cl_pdf = resume_p.parent / "cover_letter.pdf"
    if not cl_pdf.exists():
        cl_txt = resume_p.parent / "cover_letter.txt"
        if not cl_txt.exists():
            raise HTTPException(404, "Cover letter PDF not found")
        try:
            from pipeline.pdf_generator import generate_cover_letter_pdf
            generate_cover_letter_pdf(cl_txt.read_text(encoding="utf-8"), dict(row), cl_pdf)
        except Exception as e:
            raise HTTPException(500, f"Could not render cover letter PDF: {e}")
    return FileResponse(str(cl_pdf), media_type="application/pdf",
                        headers={"Content-Disposition": "inline; filename=cover_letter.pdf"})


class CoverLetterPatch(BaseModel):
    text: str


@app.patch("/api/jobs/{job_id}/cover_letter")
def api_patch_cover_letter(job_id: int, body: CoverLetterPatch) -> dict:
    row = db().execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    if not row or not row["resume_path"]:
        raise HTTPException(404, "No resume path")
    resume_p = _resolve_resume_path(str(row["resume_path"]))
    # If we can't find the original, write next to where it should be relative to ROOT
    if resume_p:
        cl_txt = resume_p.parent / "cover_letter.txt"
    else:
        stored = Path(str(row["resume_path"]).replace("\\", "/"))
        cl_txt = ROOT / "output" / "resumes" / Path(*stored.parts[-2:]).parent / "cover_letter.txt"
    cl_txt.parent.mkdir(parents=True, exist_ok=True)
    cl_txt.write_text(body.text, encoding="utf-8")
    pdf_updated = False
    try:
        from pipeline.pdf_generator import generate_cover_letter_pdf
        generate_cover_letter_pdf(body.text, dict(row), cl_txt.parent / "cover_letter.pdf")
        pdf_updated = True
    except Exception:
        # Keep the text edit even if PDF rendering is unavailable.
        pass
    return {"status": "ok", "pdf_updated": pdf_updated}


# ── Import ────────────────────────────────────────────────────────────────────


class ImportJob(BaseModel):
    title: str
    company: str
    url: str = ""
    status: str = "applied"
    date_applied: str | None = None
    location: str = ""
    notes: str = ""


@app.post("/api/jobs/import")
def api_import_job(body: ImportJob) -> dict:
    conn = db()
    url = body.url.strip()
    if not url:
        raw = f"{body.title.lower()}|{body.company.lower()}|{body.date_applied or ''}"
        h = hashlib.md5(raw.encode()).hexdigest()[:10]
        slug = re.sub(r"[^a-z0-9]+", "-", body.company.lower())[:24].strip("-")
        url = f"manual://{slug}/{h}"

    try:
        conn.execute("""
            INSERT INTO jobs (title, company, location, url, source, score,
                             status, date_applied, notes, date_scraped)
            VALUES (?, ?, ?, ?, 'manual', 1.0, ?, ?, ?, datetime('now'))
        """, (body.title, body.company, body.location, url,
              body.status, body.date_applied, body.notes or None))
        conn.commit()
        conn.execute("PRAGMA wal_checkpoint(PASSIVE)")
        job_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        return {"status": "created", "id": job_id, "message": f"Added: {body.title}"}
    except sqlite3.IntegrityError:
        existing = conn.execute("SELECT id, status FROM jobs WHERE url = ?", (url,)).fetchone()
        if existing:
            update_status(conn, existing["id"], body.status,
                          date_applied=body.date_applied, notes=body.notes or None)
            return {"status": "updated", "id": existing["id"], "message": f"Updated: {body.title}"}
        raise HTTPException(409, "URL conflict")


# ── Recruiters ────────────────────────────────────────────────────────────────


class RecruiterIn(BaseModel):
    name: str
    email: str | None = None
    company: str | None = None
    title: str | None = None
    linkedin_url: str | None = None
    source: str = "manual"
    notes: str | None = None


class RecruiterPatch(BaseModel):
    name: str | None = None
    email: str | None = None
    company: str | None = None
    title: str | None = None
    linkedin_url: str | None = None
    source: str | None = None
    notes: str | None = None


@app.get("/api/recruiters")
def api_list_recruiters() -> list[dict]:
    return [dict(r) for r in list_recruiters(db())]


@app.post("/api/recruiters")
def api_add_recruiter(body: RecruiterIn) -> dict:
    conn = db()
    email = (body.email or "").strip()
    if email:
        existing = get_recruiter_by_email(conn, email)
        if existing:
            raise HTTPException(409, f"Recruiter with email {email} already exists")
    try:
        rid = add_recruiter(
            conn, body.name, email=body.email, company=body.company,
            title=body.title, linkedin_url=body.linkedin_url,
            source=body.source, notes=body.notes,
        )
    except sqlite3.IntegrityError:
        raise HTTPException(409, "Recruiter with that email already exists")
    return dict(get_recruiter(conn, rid))


@app.get("/api/recruiters/{recruiter_id}")
def api_get_recruiter(recruiter_id: int) -> dict:
    r = get_recruiter(db(), recruiter_id)
    if not r:
        raise HTTPException(404, "Recruiter not found")
    return dict(r)


@app.patch("/api/recruiters/{recruiter_id}")
def api_patch_recruiter(recruiter_id: int, patch: RecruiterPatch) -> dict:
    conn = db()
    if not get_recruiter(conn, recruiter_id):
        raise HTTPException(404, "Recruiter not found")
    try:
        update_recruiter(conn, recruiter_id, **patch.model_dump(exclude_unset=True))
    except sqlite3.IntegrityError:
        raise HTTPException(409, "Another recruiter already uses that email")
    return dict(get_recruiter(conn, recruiter_id))


@app.delete("/api/recruiters/{recruiter_id}")
def api_delete_recruiter(recruiter_id: int) -> dict:
    conn = db()
    if not get_recruiter(conn, recruiter_id):
        raise HTTPException(404, "Recruiter not found")
    delete_recruiter(conn, recruiter_id)
    return {"status": "deleted", "id": recruiter_id}


@app.get("/api/recruiters/{recruiter_id}/outreach")
def api_recruiter_outreach(recruiter_id: int) -> list[dict]:
    conn = db()
    if not get_recruiter(conn, recruiter_id):
        raise HTTPException(404, "Recruiter not found")
    return [dict(o) for o in list_outreach_for_recruiter(conn, recruiter_id)]


# ── Outreach ──────────────────────────────────────────────────────────────────


class OutreachIn(BaseModel):
    recruiter_id: int
    job_id: int | None = None
    type: str = "cold_email"
    subject: str | None = None
    body: str | None = None
    status: str = "draft"


class OutreachPatch(BaseModel):
    type: str | None = None
    subject: str | None = None
    body: str | None = None
    status: str | None = None
    sent_at: str | None = None
    reply_received_at: str | None = None
    follow_up_date: str | None = None
    notes: str | None = None
    job_id: int | None = None


@app.post("/api/outreach")
def api_add_outreach(body: OutreachIn) -> dict:
    conn = db()
    if not get_recruiter(conn, body.recruiter_id):
        raise HTTPException(404, "Recruiter not found")
    oid = add_outreach(
        conn, body.recruiter_id, type=body.type, subject=body.subject,
        body=body.body, job_id=body.job_id, status=body.status,
    )
    return dict(get_outreach(conn, oid))


@app.patch("/api/outreach/{outreach_id}")
def api_patch_outreach(outreach_id: int, patch: OutreachPatch) -> dict:
    conn = db()
    if not get_outreach(conn, outreach_id):
        raise HTTPException(404, "Outreach not found")
    update_outreach(conn, outreach_id, **patch.model_dump(exclude_unset=True))
    return dict(get_outreach(conn, outreach_id))


class OutreachDraft(BaseModel):
    recruiter_id: int
    job_id: int | None = None
    type: str = "cold"  # "cold" | "referral"


@app.post("/api/outreach/draft")
def api_draft_outreach(body: OutreachDraft) -> dict:
    """LLM-generate a cold email / referral ask and save it as a draft outreach
    record. Returns {id, subject, body}."""
    conn = db()
    recruiter = get_recruiter(conn, body.recruiter_id)
    if not recruiter:
        raise HTTPException(404, "Recruiter not found")

    job = None
    if body.job_id is not None:
        job_row = conn.execute("SELECT * FROM jobs WHERE id = ?", (body.job_id,)).fetchone()
        if not job_row:
            raise HTTPException(404, "Job not found")
        job = dict(job_row)

    is_referral = body.type == "referral"
    try:
        from pipeline.email_generator import generate_cold_email, COLD, REFERRAL
        draft = generate_cold_email(
            dict(recruiter), job, profile=None,
            email_type=REFERRAL if is_referral else COLD,
        )
    except (ImportError, ModuleNotFoundError) as e:
        raise HTTPException(503, f"Email generator unavailable: {e}")
    except Exception as e:
        raise HTTPException(500, f"Email generation failed: {e}")

    stored_type = OUTREACH_REFERRAL if is_referral else OUTREACH_COLD
    oid = add_outreach(
        conn, body.recruiter_id, type=stored_type,
        subject=draft.get("subject"), body=draft.get("body"), job_id=body.job_id,
    )
    return {"id": oid, "subject": draft.get("subject", ""), "body": draft.get("body", "")}


@app.post("/api/outreach/{outreach_id}/send")
def api_send_outreach(outreach_id: int) -> dict:
    """Send a draft outreach email via Gmail SMTP, then mark it sent and set a
    7-day follow-up reminder."""
    from datetime import datetime, timedelta

    conn = db()
    o = get_outreach(conn, outreach_id)
    if not o:
        raise HTTPException(404, "Outreach not found")
    recruiter = get_recruiter(conn, o["recruiter_id"])
    to = ((recruiter["email"] if recruiter else "") or "").strip()
    if not to:
        raise HTTPException(400, "Recruiter has no email address — add one first")

    try:
        from pipeline.email_sender import send_email
    except (ImportError, ModuleNotFoundError) as e:
        raise HTTPException(503, f"Email sender unavailable: {e}")

    if not send_email(to, o["subject"] or "", o["body"] or ""):
        raise HTTPException(502, "Email send failed — check GMAIL_ADDRESS / GMAIL_APP_PASSWORD")

    now = datetime.utcnow()
    sent_at = now.isoformat()
    follow_up = (now + timedelta(days=7)).date().isoformat()
    update_outreach_status(conn, outreach_id, OUTREACH_SENT, sent_at=sent_at, follow_up_date=follow_up)
    return {"sent": True, "to": to, "sent_at": sent_at, "follow_up_date": follow_up}


@app.get("/api/outreach/followups")
def api_outreach_followups() -> list[dict]:
    """Sent outreach due for follow-up (follow_up_date <= today), for the banner."""
    from datetime import date as _date
    return [dict(r) for r in list_followups_due(db(), _date.today().isoformat())]


@app.get("/api/email-finder")
def api_email_finder(
    first: str, last: str, domain: str = "", probe: bool = True,
    linkedin_url: str | None = None,
) -> list[str]:
    """Best-effort recruiter email guesses, ranked. A LinkedIn URL alone works
    (Prospeo resolves it login-free); a domain enables verification + pattern
    inference. SMTP probing (probe=true) is often blocked/inconclusive."""
    from pipeline.email_finder import guess_emails
    return guess_emails(first, last, domain, probe=probe, linkedin_url=linkedin_url)


# ── Recruiting timeline (M19) ────────────────────────────────────────────────

CALENDAR_PATH = ROOT / "config" / "recruiting_calendar.json"

# Job statuses that mean "a role you could still apply to" — used to count the
# live open roles surfaced next to each calendar company.
_APPLYABLE_STATUSES = {STATUS_NEW, STATUS_QUEUED, STATUS_APPROVED}


def _load_calendar() -> dict:
    try:
        return json.loads(CALENDAR_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"companies": []}


def _company_window_status(comp: dict, today) -> dict:
    """Compute a company's window status relative to `today` (a date).
    Returns {status, days_until_open?, days_until_close?}. Status is one of
    upcoming / rolling / open / closing_soon / closed."""
    from datetime import date as _date

    def _parse(d):
        try:
            return _date.fromisoformat(d) if d else None
        except (TypeError, ValueError):
            return None

    opens = _parse(comp.get("opens"))
    closes = _parse(comp.get("closes"))
    rolling = bool(comp.get("rolling"))

    if opens and today < opens:
        return {"status": "upcoming", "days_until_open": (opens - today).days}

    if rolling:
        if closes and today > closes:
            return {"status": "closed"}
        return {"status": "rolling"}

    if closes:
        if today > closes:
            return {"status": "closed"}
        days_left = (closes - today).days
        return {
            "status": "closing_soon" if days_left <= 14 else "open",
            "days_until_close": days_left,
        }

    return {"status": "open"}


@app.get("/api/timeline")
def api_timeline() -> dict:
    """Curated per-company application windows, each annotated with computed
    window status, live open-role count from the scraped jobs, and whether a
    recruiter/contact already exists for that company."""
    from datetime import date as _date

    cal = _load_calendar()
    companies = cal.get("companies", [])
    today = _date.today()

    conn = db()
    # Pull applyable jobs + recruiter companies once, match by alias in Python.
    job_rows = conn.execute(
        "SELECT company, status FROM jobs WHERE status IN (?, ?, ?)",
        (STATUS_NEW, STATUS_QUEUED, STATUS_APPROVED),
    ).fetchall()
    job_companies = [((r["company"] or "").lower(), r["status"]) for r in job_rows]
    recruiter_companies = [
        (r["company"] or "").lower()
        for r in conn.execute("SELECT company FROM recruiters").fetchall()
    ]

    out = []
    for comp in companies:
        aliases = [a.lower() for a in comp.get("aliases", []) if a] or [comp.get("name", "").lower()]
        open_roles = sum(
            1 for (jc, st) in job_companies
            if jc and any(a in jc for a in aliases) and st in _APPLYABLE_STATUSES
        )
        has_contact = any(
            rc and any(a in rc for a in aliases) for rc in recruiter_companies
        )
        merged = {**comp, **_company_window_status(comp, today),
                  "open_roles": open_roles, "has_contact": has_contact}
        out.append(merged)

    return {
        "cycle": cal.get("cycle", ""),
        "note": cal.get("note", ""),
        "generated": cal.get("generated", ""),
        "today": today.isoformat(),
        "companies": out,
    }


# ── Reminders (M19) ──────────────────────────────────────────────────────────


class ReminderIn(BaseModel):
    company: str
    kind: str = "apply"          # "apply" | "reach_out"
    due_date: str | None = None
    note: str | None = None


class ReminderPatch(BaseModel):
    company: str | None = None
    kind: str | None = None
    due_date: str | None = None
    done: int | None = None
    note: str | None = None


@app.get("/api/reminders")
def api_list_reminders(include_done: bool = True) -> list[dict]:
    return [dict(r) for r in list_reminders(db(), include_done=include_done)]


@app.get("/api/reminders/due")
def api_reminders_due() -> list[dict]:
    """Open reminders due on/before today, for the banner."""
    from datetime import date as _date
    return [dict(r) for r in list_reminders_due(db(), _date.today().isoformat())]


@app.post("/api/reminders")
def api_add_reminder(body: ReminderIn) -> dict:
    conn = db()
    if not body.company.strip():
        raise HTTPException(400, "company is required")
    rid = add_reminder(
        conn, body.company.strip(), kind=body.kind or REMINDER_APPLY,
        due_date=body.due_date, note=body.note,
    )
    return dict(get_reminder(conn, rid))


@app.patch("/api/reminders/{reminder_id}")
def api_patch_reminder(reminder_id: int, patch: ReminderPatch) -> dict:
    conn = db()
    if not get_reminder(conn, reminder_id):
        raise HTTPException(404, "Reminder not found")
    update_reminder(conn, reminder_id, **patch.model_dump(exclude_unset=True))
    return dict(get_reminder(conn, reminder_id))


@app.delete("/api/reminders/{reminder_id}")
def api_delete_reminder(reminder_id: int) -> dict:
    conn = db()
    if not get_reminder(conn, reminder_id):
        raise HTTPException(404, "Reminder not found")
    delete_reminder(conn, reminder_id)
    return {"status": "deleted", "id": reminder_id}


# ── Interview prep (M9) ───────────────────────────────────────────────────────


@app.get("/api/prep")
def api_list_prep_jobs() -> list[dict]:
    """Jobs at an interview stage (oa / interview) with a has_prep flag."""
    return [dict(r) for r in list_prep_jobs(db())]


@app.get("/api/jobs/{job_id}/prep")
def api_get_prep(job_id: int) -> dict:
    """The stored interview-prep pack for a job (404 if none generated yet)."""
    row = get_prep(db(), job_id)
    if not row:
        raise HTTPException(404, "No prep generated yet")
    try:
        content = json.loads(row["content"]) if row["content"] else {}
    except ValueError:
        content = {}
    return {"job_id": job_id, "content": content,
            "model": row["model"], "updated_at": row["updated_at"]}


@app.post("/api/jobs/{job_id}/prep")
def api_generate_prep(job_id: int) -> dict:
    """Generate (or regenerate) an interview-prep pack for a job and store it."""
    conn = db()
    row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Job not found")
    job = dict(row)

    # Prefer the stored description; fall back to fetching the full JD if thin.
    jd_text = job.get("description") or ""
    if len(jd_text) < 200 and job.get("url"):
        try:
            from pipeline.jd_fetcher import fetch_jd
            fetched = fetch_jd(job["url"])
            if fetched:
                jd_text = fetched
        except Exception:
            pass  # stored description is enough to proceed

    try:
        from pipeline.interview_prep import generate_prep
        from pipeline.llm_client import get_provider_model
        pack = generate_prep(job, jd_text)
    except (ImportError, ModuleNotFoundError) as e:
        raise HTTPException(503, f"Interview-prep module unavailable: {e}")
    except Exception as e:
        raise HTTPException(500, f"Prep generation failed: {e}")

    if not pack:
        raise HTTPException(500, "Prep generation failed — check the LLM API key")

    model = None
    try:
        model = get_provider_model()
    except Exception:
        pass
    upsert_prep(conn, job_id, json.dumps(pack), model=model)
    return {"job_id": job_id, "content": pack, "model": model}


@app.delete("/api/jobs/{job_id}/prep")
def api_delete_prep(job_id: int) -> dict:
    conn = db()
    if not get_prep(conn, job_id):
        raise HTTPException(404, "No prep to delete")
    delete_prep(conn, job_id)
    return {"status": "deleted", "job_id": job_id}


# ── Settings persistence (M7) ─────────────────────────────────────────────────
# Reads/writes the functional keys in config/settings.yaml (LLM provider/models,
# min score, sponsor filter, source toggles). API keys are NOT here — they are
# environment variables. NOTE: writing reformats the YAML (comments are dropped).

SETTINGS_PATH = ROOT / "config" / "settings.yaml"
_EDITABLE_SOURCES = ("intern_list", "newgrad_jobs")
_LLM_PROVIDERS = ("groq", "gemini", "anthropic")


def _read_settings_file() -> dict:
    try:
        return yaml.safe_load(SETTINGS_PATH.read_text(encoding="utf-8")) or {}
    except (OSError, ValueError):
        return {}


@app.get("/api/settings")
def api_get_settings() -> dict:
    cfg = _read_settings_file()
    llm = cfg.get("llm", {})
    sources = cfg.get("sources", {})
    notif = cfg.get("notifications", {})
    return {
        "llm": {
            "provider": llm.get("provider", "groq"),
            "groq_model": llm.get("groq_model", ""),
            "gemini_model": llm.get("gemini_model", ""),
            "anthropic_model": llm.get("anthropic_model", ""),
        },
        "scoring": {"min_score": cfg.get("scoring", {}).get("min_score", 0.0)},
        "filters": {"require_known_sponsor": bool(cfg.get("filters", {}).get("require_known_sponsor", False))},
        "sources": {s: bool(sources.get(s, {}).get("enabled", False)) for s in _EDITABLE_SOURCES},
        "notifications": {
            "on_offer": bool(notif.get("on_offer", False)),
            "on_interview": bool(notif.get("on_interview", False)),
            "email_to": notif.get("email_to", "") or "",
        },
    }


class SettingsPatch(BaseModel):
    llm: dict | None = None
    scoring: dict | None = None
    filters: dict | None = None
    sources: dict | None = None
    notifications: dict | None = None


@app.post("/api/settings")
def api_save_settings(body: SettingsPatch) -> dict:
    cfg = _read_settings_file()

    if body.llm:
        llm = cfg.setdefault("llm", {})
        for k in ("provider", "groq_model", "gemini_model", "anthropic_model"):
            if body.llm.get(k) is not None:
                llm[k] = body.llm[k]
    if body.scoring and body.scoring.get("min_score") is not None:
        cfg.setdefault("scoring", {})["min_score"] = float(body.scoring["min_score"])
    if body.filters and "require_known_sponsor" in body.filters:
        cfg.setdefault("filters", {})["require_known_sponsor"] = bool(body.filters["require_known_sponsor"])
    if body.sources:
        sources = cfg.setdefault("sources", {})
        for s in _EDITABLE_SOURCES:
            if s in body.sources:
                sources.setdefault(s, {})["enabled"] = bool(body.sources[s])
    if body.notifications:
        n = cfg.setdefault("notifications", {})
        for k in ("on_offer", "on_interview"):
            if k in body.notifications:
                n[k] = bool(body.notifications[k])
        if "email_to" in body.notifications:
            n["email_to"] = (body.notifications["email_to"] or "").strip()

    provider = cfg.get("llm", {}).get("provider", "groq")
    if provider not in _LLM_PROVIDERS:
        raise HTTPException(400, f"Unknown LLM provider '{provider}' (use one of {_LLM_PROVIDERS})")

    try:
        SETTINGS_PATH.write_text(
            yaml.safe_dump(cfg, sort_keys=False, default_flow_style=False, allow_unicode=True),
            encoding="utf-8",
        )
    except OSError as e:
        raise HTTPException(500, f"Could not write settings: {e}")

    # Drop the LLM config cache so the change takes effect on the next tailor call.
    try:
        from pipeline.llm_client import reload_config
        reload_config()
    except Exception:
        pass

    return api_get_settings()


# ── Serve built React app (production) ───────────────────────────────────────

_dist = ROOT / "apps" / "web" / "dist"
if _dist.exists():
    app.mount("/", StaticFiles(directory=str(_dist), html=True), name="static")
