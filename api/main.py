"""
FastAPI backend for JobApply — React UI data layer.
Run: uvicorn api.main:app --reload --port 8000
"""

from __future__ import annotations
import hashlib
import os
import re
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from tracker.tracker import (
    init_db, get_jobs, get_stats, update_status,
    STATUS_NEW, STATUS_QUEUED, STATUS_APPROVED, STATUS_APPLIED,
    STATUS_OA, STATUS_INTERVIEW, STATUS_REJECTED, STATUS_OFFER, STATUS_SKIPPED,
)

app = FastAPI(title="JobApply API", version="2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# In production (Render), DB_PATH env var points to the persistent disk.
# Locally it falls back to tracker/applications.db in the repo.
_db_env = os.environ.get("DB_PATH")
DB_PATH = Path(_db_env) if _db_env else ROOT / "tracker" / "applications.db"

# Seed the persistent-disk DB from the repo copy on first deploy
_git_db = ROOT / "tracker" / "applications.db"
if _db_env and not DB_PATH.exists() and _git_db.exists():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(_git_db, DB_PATH)

OUTPUT_DIR = Path(os.environ.get("OUTPUT_DIR", str(ROOT / "output" / "resumes")))

# ── Singleton DB connection ───────────────────────────────────────────────────
# Uses Turso (libsql) when TURSO_DATABASE_URL is set, sqlite3 otherwise.

_conn = None


def db():
    global _conn
    if _conn is None:
        if os.environ.get("TURSO_DATABASE_URL"):
            from api.turso import connect as turso_connect
            from tracker.tracker import _create_tables  # type: ignore[attr-defined]
            _conn = turso_connect(DB_PATH)   # seeds from git DB on first boot
            _create_tables(_conn)            # create / migrate schema in Turso
        else:
            _conn = init_db(DB_PATH)         # local: plain sqlite3
    return _conn


# ── Stats ─────────────────────────────────────────────────────────────────────


@app.get("/api/stats")
def api_stats() -> dict:
    s = get_stats(db())
    return {
        "total":     sum(s.values()),
        "new":       s.get(STATUS_NEW,       0),
        "ready":     s.get(STATUS_QUEUED,    0),
        "approved":  s.get(STATUS_APPROVED,  0),
        "applied":   s.get(STATUS_APPLIED,   0),
        "oa":        s.get(STATUS_OA,        0),
        "interview": s.get(STATUS_INTERVIEW, 0),
        "offer":     s.get(STATUS_OFFER,     0),
        "rejected":  s.get(STATUS_REJECTED,  0),
        "skipped":   s.get(STATUS_SKIPPED,   0),
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

    ready_job = conn.execute(
        "SELECT * FROM jobs WHERE status=? ORDER BY score DESC LIMIT 1", (STATUS_QUEUED,)
    ).fetchone()
    if ready_job:
        j = dict(ready_job)
        items.append({
            "id": "f_approve", "type": "confirm",
            "icon": "⚡", "color": "#8B5CF6",
            "label": f"{j['company']} application awaits your approval",
            "cta": "Confirm & Apply", "tab": "ready", "jobId": j["id"],
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


@app.patch("/api/jobs/{job_id}")
def api_patch_job(job_id: int, patch: JobPatch) -> dict:
    conn = db()
    row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Job not found")

    current = dict(row)
    new_status = patch.status or current["status"]

    # Only pass non-None kwargs that update_status allows
    kwargs = {k: v for k, v in patch.model_dump(exclude={"status"}).items() if v is not None}
    update_status(conn, job_id, new_status, **kwargs)

    updated = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    return dict(updated)


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
        from pipeline.resume_tailor import tailor_resume
        from pipeline.cover_letter import generate_cover_letter
        from pipeline.pdf_generator import generate_resume_pdf, generate_cover_letter_pdf

        jd_text = fetch_jd(job["url"])
        if not jd_text:
            raise HTTPException(400, "Could not fetch job description — check URL")

        tailored = tailor_resume(job, jd_text)
        if not tailored:
            raise HTTPException(500, "Tailoring failed — check API key in Streamlit secrets")

        slug = re.sub(r"[^a-z0-9_]", "", f"{job.get('company','')}{job['title']}".lower().replace(" ", "_"))[:60]
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


@app.get("/api/jobs/{job_id}/resume")
def api_get_resume(job_id: int):
    row = db().execute("SELECT resume_path FROM jobs WHERE id = ?", (job_id,)).fetchone()
    if not row or not row["resume_path"]:
        raise HTTPException(404, "No resume found")
    p = Path(str(row["resume_path"]).replace("\\", "/"))
    if not p.is_absolute():
        p = ROOT / p
    if not p.exists():
        raise HTTPException(404, "Resume file not found on disk")
    return FileResponse(str(p), media_type="application/pdf",
                        headers={"Content-Disposition": f"inline; filename=resume.pdf"})


# ── Cover letter ──────────────────────────────────────────────────────────────


@app.get("/api/jobs/{job_id}/cover_letter")
def api_get_cover_letter(job_id: int) -> PlainTextResponse:
    row = db().execute("SELECT resume_path FROM jobs WHERE id = ?", (job_id,)).fetchone()
    if not row or not row["resume_path"]:
        raise HTTPException(404, "No resume path")
    cl_txt = Path(str(row["resume_path"]).replace("\\", "/")).parent / "cover_letter.txt"
    if not cl_txt.is_absolute():
        cl_txt = ROOT / cl_txt
    if not cl_txt.exists():
        raise HTTPException(404, "Cover letter not found")
    return PlainTextResponse(cl_txt.read_text(encoding="utf-8"))


class CoverLetterPatch(BaseModel):
    text: str


@app.patch("/api/jobs/{job_id}/cover_letter")
def api_patch_cover_letter(job_id: int, body: CoverLetterPatch) -> dict:
    row = db().execute("SELECT resume_path FROM jobs WHERE id = ?", (job_id,)).fetchone()
    if not row or not row["resume_path"]:
        raise HTTPException(404, "No resume path")
    cl_txt = Path(str(row["resume_path"]).replace("\\", "/")).parent / "cover_letter.txt"
    if not cl_txt.is_absolute():
        cl_txt = ROOT / cl_txt
    cl_txt.parent.mkdir(parents=True, exist_ok=True)
    cl_txt.write_text(body.text, encoding="utf-8")
    return {"status": "ok"}


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


# ── Serve built React app (production) ───────────────────────────────────────

_dist = ROOT / "web" / "dist"
if _dist.exists():
    app.mount("/", StaticFiles(directory=str(_dist), html=True), name="static")
