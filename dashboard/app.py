"""
JobApply Review Dashboard
Run: streamlit run dashboard/app.py
"""

import csv
import io
import math
import os
import re
import sqlite3
import subprocess
import sys
from datetime import date
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

sys.path.insert(0, str(Path(__file__).parent.parent))

# Inject Streamlit secrets into env so pipeline modules pick them up
for _key in ("GOOGLE_API_KEY", "ANTHROPIC_API_KEY"):
    if _key in st.secrets:
        os.environ[_key] = st.secrets[_key]

# Streamlit Cloud mounts the repo under /mount/src — headed browser unavailable
IS_CLOUD = Path("/mount/src").exists()

from tracker.tracker import (
    init_db, get_jobs, get_stats, update_status,
    STATUS_NEW, STATUS_QUEUED, STATUS_APPROVED, STATUS_SKIPPED,
    STATUS_APPLIED, STATUS_INTERVIEW, STATUS_REJECTED, STATUS_OFFER,
)

DB_PATH        = Path(__file__).parent.parent / "tracker" / "applications.db"
OUTPUT_DIR     = Path(__file__).parent.parent / "output" / "resumes"
SCREENSHOT_DIR = Path(__file__).parent.parent / "output" / "apply_screenshots"
ROOT_DIR       = Path(__file__).parent.parent

PAGE_SIZE_NEW = 25
PAGE_SIZE_ALL = 50

st.set_page_config(
    page_title="JobApply",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ─────────────────────────────────────────────────────────────────

st.markdown("""
<style>
/* Funnel header */
.funnel-header {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
    padding: 1.2rem 2rem;
    border-radius: 12px;
    margin-bottom: 1rem;
    color: white;
    display: flex;
    align-items: center;
    justify-content: space-between;
}
.funnel-header h1 { margin: 0; font-size: 1.5rem; color: white; }
.funnel-header p  { margin: 0.2rem 0 0; opacity: 0.7; font-size: 0.85rem; }
.funnel-steps {
    display: flex; align-items: center; gap: 0.4rem;
    font-size: 0.82rem;
}
.funnel-step {
    background: rgba(255,255,255,0.12);
    padding: 0.25rem 0.7rem;
    border-radius: 20px;
    color: white;
    white-space: nowrap;
}
.funnel-step.active { background: rgba(255,255,255,0.28); font-weight: 700; }
.funnel-arrow { opacity: 0.45; font-size: 0.75rem; }
.funnel-rate  { opacity: 0.55; font-size: 0.7rem; margin-left: 0.15rem; }

/* Score bar */
.score-bar-wrap { height: 6px; background: #e0e0e0; border-radius: 3px; }
.score-bar      { height: 6px; border-radius: 3px; }

/* Compact job row */
.compact-row {
    display: flex; align-items: center; gap: 0.75rem;
    padding: 0.1rem 0;
}

/* Status pill */
.pill {
    display: inline-block; padding: 2px 10px; border-radius: 20px;
    font-size: 0.75rem; font-weight: 600;
}
.pill-new      { background:#e3f2fd; color:#1565c0; }
.pill-queued   { background:#e8f5e9; color:#2e7d32; }
.pill-approved { background:#ede7f6; color:#4527a0; }
.pill-applied  { background:#fff3e0; color:#e65100; }
.pill-interview{ background:#f3e5f5; color:#6a1b9a; }
.pill-offer    { background:#e8f5e9; color:#1b5e20; }
.pill-rejected { background:#ffebee; color:#b71c1c; }
.pill-skipped  { background:#f5f5f5; color:#616161; }

/* All-tab row left border by status */
.row-new       { border-left: 4px solid #1565c0; padding-left: 0.6rem; }
.row-queued    { border-left: 4px solid #2e7d32; padding-left: 0.6rem; }
.row-approved  { border-left: 4px solid #4527a0; padding-left: 0.6rem; }
.row-applied   { border-left: 4px solid #e65100; padding-left: 0.6rem; }
.row-interview { border-left: 4px solid #6a1b9a; padding-left: 0.6rem; }
.row-offer     { border-left: 4px solid #1b5e20; padding-left: 0.6rem; }
.row-rejected  { border-left: 4px solid #b71c1c; padding-left: 0.6rem; }
.row-skipped   { border-left: 4px solid #9e9e9e; padding-left: 0.6rem; }

/* Section label */
.section-label {
    font-size: 0.7rem; font-weight: 700; letter-spacing: 0.08em;
    text-transform: uppercase; color: #888; margin: 1rem 0 0.4rem;
}

/* Action button row */
.action-hint { font-size: 0.72rem; color: #888; margin-top: 0.2rem; }
</style>
""", unsafe_allow_html=True)


# ── Helpers ────────────────────────────────────────────────────────────────────

@st.cache_resource
def get_conn() -> sqlite3.Connection:
    conn = init_db(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn



def refresh(toast_msg: str | None = None) -> None:
    if toast_msg:
        st.toast(toast_msg)
    st.cache_resource.clear()
    st.cache_data.clear()
    st.rerun()


def rows_to_dicts(rows) -> list[dict]:
    return [dict(r) for r in rows]


def score_color(score: float) -> str:
    if score >= 0.7: return "🟢"
    if score >= 0.5: return "🟡"
    return "🔴"


def score_bar_html(score: float) -> str:
    pct = int(score * 100)
    color = "#4caf50" if score >= 0.7 else "#ff9800" if score >= 0.5 else "#f44336"
    return (
        f'<div class="score-bar-wrap" title="AI relevance score: {pct}% match with your profile">'
        f'<div class="score-bar" style="width:{pct}%;background:{color};"></div>'
        f'</div>'
    )


STATUS_META = {
    STATUS_NEW:       ("🆕", "New",       "pill-new"),
    STATUS_QUEUED:    ("✅", "Ready",     "pill-queued"),
    STATUS_APPROVED:  ("🚀", "Approved",  "pill-approved"),
    STATUS_SKIPPED:   ("⏭", "Skipped",   "pill-skipped"),
    STATUS_APPLIED:   ("📤", "Applied",   "pill-applied"),
    STATUS_INTERVIEW: ("🎤", "Interview", "pill-interview"),
    STATUS_REJECTED:  ("❌", "Rejected",  "pill-rejected"),
    STATUS_OFFER:     ("🎉", "Offer",     "pill-offer"),
}

STATUS_ROW_CLASS = {
    STATUS_NEW:       "row-new",
    STATUS_QUEUED:    "row-queued",
    STATUS_APPROVED:  "row-approved",
    STATUS_APPLIED:   "row-applied",
    STATUS_INTERVIEW: "row-interview",
    STATUS_OFFER:     "row-offer",
    STATUS_REJECTED:  "row-rejected",
    STATUS_SKIPPED:   "row-skipped",
}


def status_pill(status: str) -> str:
    icon, label, cls = STATUS_META.get(status, ("", status, "pill-skipped"))
    return f'<span class="pill {cls}">{icon} {label}</span>'


def _resolve_path(stored: str) -> Path | None:
    """Resolve a stored path to absolute, handling Windows backslashes and relative paths."""
    if not stored:
        return None
    p = Path(stored.replace("\\", "/"))
    if not p.is_absolute():
        p = ROOT_DIR / p
    return p if p.exists() else None


def pdf_viewer(path: str, dl_key: str = "") -> None:
    """Render PDF pages as images — works in all browsers, no data: URI needed."""
    p = _resolve_path(path)
    if p is None:
        st.info("PDF not generated in this environment — click ✨ Tailor to create it here.")
        return
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(str(p))
        for i in range(len(doc)):
            page = doc.load_page(i)
            pix  = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2× zoom for readability
            st.image(pix.tobytes("png"), use_container_width=True)
        doc.close()
    except Exception as e:
        st.warning(f"Could not render PDF: {e}")
    # Unique key: caller supplies a job-scoped prefix so duplicate filenames never collide
    _key = f"dl_{dl_key}_{re.sub(r'[^a-z0-9]', '_', str(p).lower())[-30:]}"
    st.download_button(
        "⬇️ Download PDF",
        data=p.read_bytes(),
        file_name=p.name,
        mime="application/pdf",
        key=_key,
    )


def open_file(path: str) -> None:
    if IS_CLOUD:
        return
    try:
        os.startfile(path)
    except AttributeError:
        subprocess.run(["xdg-open", path])


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9_]", "", text.lower().replace(" ", "_"))[:60]


def _run_tailor(limit: int) -> tuple[bool, str]:
    result = subprocess.run(
        [sys.executable, "main.py", "--tailor", "--limit", str(limit)],
        capture_output=True, text=True, cwd=ROOT_DIR,
    )
    return result.returncode == 0, result.stdout + result.stderr


def _screenshot_path(job: dict) -> Path | None:
    """Return path to dry-run screenshot if it exists for this job."""
    slug = "".join(
        c if c.isalnum() else "_"
        for c in f"{job.get('company', '')}_{job['title']}"
    )[:50]
    p = SCREENSHOT_DIR / f"{slug}.png"
    return p if p.exists() else None


def _run_dry_run(job_id: int | None = None, limit: int = 10) -> tuple[bool, str]:
    """Run dry-run apply (fills form + screenshots, no submit)."""
    cmd = [sys.executable, "main.py", "--apply", "--dry-run", "--limit", str(limit)]
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT_DIR)
    return result.returncode == 0, result.stdout + result.stderr


# ── Sidebar ────────────────────────────────────────────────────────────────────

def sidebar(conn: sqlite3.Connection) -> None:
    stats = get_stats(conn)
    with st.sidebar:
        st.markdown("## 🎯 JobApply")
        st.caption("AI/ML Internship Hunter · Summer 2026")
        st.divider()

        total = sum(stats.values())

        # Funnel metrics
        st.markdown('<p class="section-label">Pipeline</p>', unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        c1.metric("Total",    total)
        c2.metric("Ready",    stats.get(STATUS_QUEUED, 0))
        c3.metric("Applied",  stats.get(STATUS_APPLIED, 0))

        c4, c5, c6 = st.columns(3)
        c4.metric("New",         stats.get(STATUS_NEW, 0))
        c5.metric("🚀 Approved", stats.get(STATUS_APPROVED, 0))
        c6.metric("Offer 🎉",    stats.get(STATUS_OFFER, 0))

        # Progress bar: applied / total
        if total:
            applied_pct = (
                stats.get(STATUS_APPLIED, 0)
                + stats.get(STATUS_INTERVIEW, 0)
                + stats.get(STATUS_OFFER, 0)
            ) / total
            st.progress(applied_pct, text=f"Applied: {applied_pct:.0%}")

        st.divider()
        st.markdown('<p class="section-label">Actions</p>', unsafe_allow_html=True)

        if not IS_CLOUD:
            if st.button("🔍 Run Discovery", use_container_width=True):
                with st.spinner("Scraping intern-list.com..."):
                    r = subprocess.run(
                        [sys.executable, "main.py", "--source", "intern_list"],
                        capture_output=True, text=True, cwd=ROOT_DIR,
                    )
                if r.returncode == 0:
                    refresh("✅ Discovery complete!")
                else:
                    st.error(r.stderr[-400:])
        else:
            st.caption("🤖 Discovery runs daily via GitHub Actions.")

        n_tailor = st.number_input("Jobs to tailor", min_value=1, max_value=50, value=10, step=5)
        if st.button("✨ Tailor Jobs", use_container_width=True, type="primary"):
            with st.spinner(f"Tailoring {n_tailor} jobs..."):
                ok, out = _run_tailor(n_tailor)
            if ok:
                refresh("✨ Tailoring done! Check Ready tab.")
            else:
                st.error(out[-400:])

        if not IS_CLOUD:
            st.divider()
            st.markdown('<p class="section-label">Dry Run</p>', unsafe_allow_html=True)
            st.caption("Fills forms + saves screenshots without submitting.")
            n_dry = st.number_input("Jobs to dry-run", min_value=1, max_value=20,
                                    value=5, step=1, key="n_dry")
            if st.button("🔍 Dry Run Queued", use_container_width=True):
                with st.spinner(f"Dry-running {n_dry} jobs (browser will open)…"):
                    ok, out = _run_dry_run(limit=n_dry)
                if ok:
                    refresh("📸 Done! Screenshots saved.")
                else:
                    st.error(out[-400:])

        if st.button("🔄 Refresh", use_container_width=True):
            refresh()

        st.divider()
        st.caption("Powered by Gemini 2.5 Flash · ReportLab · Playwright")


# ── Action buttons (simplified) ────────────────────────────────────────────────

def _action_buttons(conn: sqlite3.Connection, job: dict) -> None:
    """
    Show only the next logical primary action prominently.
    Secondary actions appear as small buttons beneath.
    """
    status = job["status"]
    jid    = job["id"]

    # Primary action
    if status == STATUS_NEW:
        if st.button("✨ Tailor", key=f"tailor_{jid}", type="primary",
                     use_container_width=True,
                     help="Generate tailored resume + cover letter with AI"):
            _tailor_single(conn, job)

    elif status == STATUS_QUEUED:
        if st.button("🚀 Approve for Auto-Apply", key=f"approve_{jid}", type="primary",
                     use_container_width=True,
                     help="Mark as approved — GHA will submit it headlessly"):
            update_status(conn, jid, STATUS_APPROVED)
            refresh(f"🚀 Approved: {job['title']} @ {job.get('company', '')}")

    elif status == STATUS_APPROVED:
        if st.button("📤 Mark Applied", key=f"apply2_{jid}", type="primary",
                     use_container_width=True):
            update_status(conn, jid, STATUS_APPLIED)
            refresh(f"📤 Marked applied: {job['title']}")

    elif status == STATUS_APPLIED:
        if st.button("🎤 Got Interview!", key=f"int2_{jid}", type="primary",
                     use_container_width=True):
            update_status(conn, jid, STATUS_INTERVIEW)
            refresh(f"🎤 Interview stage: {job['title']}")

    elif status == STATUS_INTERVIEW:
        if st.button("🎉 Got Offer!", key=f"offer_{jid}", type="primary",
                     use_container_width=True):
            update_status(conn, jid, STATUS_OFFER)
            refresh(f"🎉 OFFER from {job.get('company', '')}!")

    # Secondary actions — small row beneath primary
    sec = st.columns(5)
    col_idx = 0

    if status == STATUS_QUEUED:
        if not IS_CLOUD:
            if sec[col_idx].button("🔍 Dry Run", key=f"dry_{jid}",
                                   use_container_width=True,
                                   help="Fill form + screenshot, no submit"):
                with st.spinner("Opening browser for dry run…"):
                    _run_dry_run(limit=1)
                st.toast("📸 Dry run done — check Form Preview tab.")
                st.rerun()
            col_idx += 1
        if sec[col_idx].button("📤 Applied", key=f"apply_{jid}",
                                use_container_width=True, help="Mark as manually applied"):
            update_status(conn, jid, STATUS_APPLIED)
            refresh(f"📤 Marked applied: {job['title']}")
        col_idx += 1
        if sec[col_idx].button("🎤 Interview", key=f"int_{jid}", use_container_width=True):
            update_status(conn, jid, STATUS_INTERVIEW)
            refresh(f"🎤 Interview stage: {job['title']}")
        col_idx += 1

    if status == STATUS_APPROVED:
        if sec[col_idx].button("↩ Unapprove", key=f"unapprove_{jid}",
                                use_container_width=True):
            update_status(conn, jid, STATUS_QUEUED)
            refresh("↩ Moved back to Ready.")
        col_idx += 1

    if status not in (STATUS_SKIPPED, STATUS_REJECTED, STATUS_OFFER):
        skip_col = 3
        rej_col  = 4
        if sec[skip_col].button("⏭ Skip", key=f"skip_{jid}", use_container_width=True):
            update_status(conn, jid, STATUS_SKIPPED)
            refresh(f"⏭ Skipped: {job['title']}")
        if sec[rej_col].button("❌ Reject", key=f"rej_{jid}", use_container_width=True):
            update_status(conn, jid, STATUS_REJECTED)
            refresh(f"❌ Rejected: {job['title']}")


# ── Job card (full) ─────────────────────────────────────────────────────────────

def job_card(conn: sqlite3.Connection, job: dict, show_pdf: bool = True) -> None:
    score  = job.get("score", 0.0)
    status = job["status"]

    with st.container(border=True):
        # Header row
        h1, h2 = st.columns([7, 1])
        with h1:
            st.markdown(f"### {job['title']}")
            st.markdown(
                f"{status_pill(status)} &nbsp;"
                f"**{job.get('company') or 'Unknown'}** &nbsp;·&nbsp; "
                f"📍 {job.get('location') or 'USA'} &nbsp;·&nbsp; "
                f"Source: `{job.get('source', '?')}`",
                unsafe_allow_html=True,
            )
        with h2:
            st.link_button("Apply →", job.get("url", "#"), use_container_width=True)

        # Score bar with tooltip hint
        sc1, sc2 = st.columns([1, 8])
        sc1.markdown(
            f"{score_color(score)} **{score:.0%}**",
            help="AI relevance score — how well this role matches your profile and target keywords.",
        )
        sc2.markdown(score_bar_html(score), unsafe_allow_html=True)
        sc2.empty()

        # JD preview
        if job.get("description"):
            with st.expander("📄 Job description"):
                st.text(job["description"][:2000] + ("…" if len(job.get("description", "")) > 2000 else ""))

        # PDFs + dry-run screenshot (collapsible)
        if show_pdf and job.get("resume_path"):
            r_path    = _resolve_path(job["resume_path"]) or Path(job["resume_path"])
            cl_txt    = r_path.parent / "cover_letter.txt"
            cl_pdf    = r_path.parent / "cover_letter.pdf"
            shot_path = _screenshot_path(job)

            with st.expander("📄 View Resume & Cover Letter", expanded=False):
                tab_labels = ["📄 Resume", "✉️ Cover Letter"]
                if shot_path:
                    tab_labels.append("🖥️ Form Preview")

                tabs = st.tabs(tab_labels)

                with tabs[0]:
                    pdf_viewer(str(r_path), dl_key=f"resume_{job['id']}")

                with tabs[1]:
                    if cl_txt.exists():
                        letter = cl_txt.read_text(encoding="utf-8")
                        edited = st.text_area("Cover letter", value=letter, height=280,
                                             key=f"cl_{job['id']}", label_visibility="collapsed")
                        c_save, _, __ = st.columns([1, 1, 4])
                        if c_save.button("💾 Save", key=f"save_cl_{job['id']}"):
                            cl_txt.write_text(edited, encoding="utf-8")
                            st.toast("💾 Cover letter saved.")
                    elif IS_CLOUD:
                        st.info("Cover letter not available — re-tailor to generate it here.")
                    pdf_viewer(str(cl_pdf), dl_key=f"cl_{job['id']}")

                if shot_path:
                    with tabs[2]:
                        st.caption("Dry-run screenshot — form as it would be submitted")
                        st.image(str(shot_path), use_container_width=True)

        # Simplified action buttons
        st.markdown("---")
        _action_buttons(conn, job)

        # Notes
        st.markdown("")
        new_notes = st.text_input(
            "Notes", value=job.get("notes") or "",
            placeholder="Add notes…", key=f"notes_{job['id']}",
            label_visibility="collapsed",
        )
        if new_notes != (job.get("notes") or ""):
            update_status(conn, job["id"], status, notes=new_notes)


def _tailor_single(conn: sqlite3.Connection, job: dict) -> None:
    from pipeline.jd_fetcher import fetch_jd
    from pipeline.resume_tailor import tailor_resume
    from pipeline.cover_letter import generate_cover_letter
    from pipeline.pdf_generator import generate_resume_pdf, generate_cover_letter_pdf

    with st.spinner(f"Tailoring for {job.get('company')}…"):
        jd_text = fetch_jd(job["url"])
        if not jd_text:
            st.error("Could not fetch job description.")
            return
        tailored = tailor_resume(job, jd_text)
        if not tailored:
            st.error("Tailoring failed — check API key.")
            return
        job_dir = OUTPUT_DIR / _slug(f"{job.get('company', '')}_{job['title']}")
        job_dir.mkdir(parents=True, exist_ok=True)
        resume_path = job_dir / "resume.pdf"
        letter_text = generate_cover_letter(job, jd_text, tailored.get("why_fit", ""))
        generate_resume_pdf(tailored, resume_path)
        if letter_text:
            generate_cover_letter_pdf(letter_text, job, job_dir / "cover_letter.pdf")
            (job_dir / "cover_letter.txt").write_text(letter_text, encoding="utf-8")
        update_status(conn, job["id"], STATUS_QUEUED, resume_path=str(resume_path))
    refresh("✨ Tailored! Check the Ready tab.")


# ── Compact job row (New tab) ───────────────────────────────────────────────────

def compact_job_row(conn: sqlite3.Connection, job: dict) -> None:
    """
    A scannable single-line row for New jobs.
    Clicking expands to the full card.
    """
    score   = job.get("score", 0.0)
    pct     = int(score * 100)
    company = job.get("company") or "Unknown"
    source  = job.get("source") or "?"
    label   = f"{score_color(score)} **{job['title']}** &nbsp;·&nbsp; {company} &nbsp; `{source}` &nbsp; {pct}%"

    with st.expander(f"{score_color(score)}  {job['title']}  ·  {company}  [{pct}%]", expanded=False):
        # Score bar inside expander
        st.markdown(score_bar_html(score), unsafe_allow_html=True)
        st.caption(
            f"📍 {job.get('location') or 'USA'} &nbsp;·&nbsp; "
            f"Source: `{source}` &nbsp;·&nbsp; "
            f"Score: {pct}% — AI relevance match with your profile"
        )
        st.link_button("🔗 View posting", job.get("url", "#"))

        if job.get("description"):
            st.text(job["description"][:800] + ("…" if len(job.get("description","")) > 800 else ""))

        st.markdown("---")
        _action_buttons(conn, job)

        new_notes = st.text_input(
            "Notes", value=job.get("notes") or "",
            placeholder="Add notes…", key=f"notes_c_{job['id']}",
            label_visibility="collapsed",
        )
        if new_notes != (job.get("notes") or ""):
            update_status(conn, job["id"], STATUS_NEW, notes=new_notes)


# ── Pagination helpers ─────────────────────────────────────────────────────────

def _paginate(jobs: list[dict], page_key: str, page_size: int) -> tuple[list[dict], int, int]:
    """Return the current page slice, current page index, and total pages."""
    if page_key not in st.session_state:
        st.session_state[page_key] = 0
    total_pages = max(1, math.ceil(len(jobs) / page_size))
    # Clamp page in case list shrank
    st.session_state[page_key] = min(st.session_state[page_key], total_pages - 1)
    page = st.session_state[page_key]
    start = page * page_size
    return jobs[start : start + page_size], page, total_pages


def _pagination_controls(page: int, total_pages: int, total_jobs: int, page_key: str, page_size: int) -> None:
    st.markdown("")
    p1, p2, p3 = st.columns([1, 3, 1])
    if p1.button("← Prev", key=f"prev_{page_key}", disabled=(page == 0)):
        st.session_state[page_key] -= 1
        st.rerun()
    p2.markdown(
        f"<div style='text-align:center;color:#888;font-size:0.85rem;padding-top:0.4rem;'>"
        f"Page {page + 1} of {total_pages} &nbsp;·&nbsp; {total_jobs} jobs total</div>",
        unsafe_allow_html=True,
    )
    if p3.button("Next →", key=f"next_{page_key}", disabled=(page >= total_pages - 1)):
        st.session_state[page_key] += 1
        st.rerun()


# ── Tabs ───────────────────────────────────────────────────────────────────────

def tab_new(conn: sqlite3.Connection) -> None:
    jobs = rows_to_dicts(get_jobs(conn, status=STATUS_NEW, limit=500))
    if not jobs:
        st.info("No new jobs yet. Run discovery from the sidebar or wait for the daily GitHub Action.")
        return

    # Filter + sort bar
    f1, f2, f3 = st.columns([4, 2, 1])
    search = f1.text_input("🔍 Filter", placeholder="company or title…", label_visibility="collapsed")
    sort   = f2.selectbox("Sort", ["Score ↓", "Score ↑", "Company"], label_visibility="collapsed",
                          key="new_sort")
    min_sc = f3.slider("Min", 0.0, 1.0, 0.0, 0.05, label_visibility="collapsed", key="new_min")

    if search:
        q = search.lower()
        jobs = [j for j in jobs if q in (j.get("title") or "").lower()
                or q in (j.get("company") or "").lower()]
        # Reset to page 0 when filtering
        st.session_state["new_page"] = 0

    jobs = [j for j in jobs if j["score"] >= min_sc]

    if sort == "Score ↓":   jobs.sort(key=lambda j: j["score"], reverse=True)
    elif sort == "Score ↑": jobs.sort(key=lambda j: j["score"])
    elif sort == "Company":  jobs.sort(key=lambda j: j.get("company") or "")

    page_jobs, page, total_pages = _paginate(jobs, "new_page", PAGE_SIZE_NEW)
    st.caption(
        f"{len(jobs)} jobs · page {page + 1}/{total_pages} · "
        f"click a row to expand → review → Tailor or Skip"
    )

    for job in page_jobs:
        compact_job_row(conn, job)

    _pagination_controls(page, total_pages, len(jobs), "new_page", PAGE_SIZE_NEW)


def tab_queued(conn: sqlite3.Connection) -> None:
    jobs = rows_to_dicts(get_jobs(conn, status=STATUS_QUEUED, limit=100))
    if not jobs:
        st.info("No jobs ready yet. Use **✨ Tailor Jobs** in the sidebar or click **✨ Tailor** on a new job.")
        return
    st.caption(f"{len(jobs)} tailored jobs — open the resume, then **🚀 Approve** or **📤 Applied**.")
    for job in jobs:
        job_card(conn, job, show_pdf=True)


def tab_approved(conn: sqlite3.Connection) -> None:
    jobs = rows_to_dicts(get_jobs(conn, status=STATUS_APPROVED, limit=100))
    if not jobs:
        st.info("No approved jobs yet. Review resumes in the **✅ Ready** tab and click **🚀 Approve**.")
        return
    st.caption(f"{len(jobs)} approved — trigger **Auto Apply** from GitHub Actions to submit headlessly.")
    for job in jobs:
        job_card(conn, job, show_pdf=True)


def tab_applied(conn: sqlite3.Connection) -> None:
    pipeline_order = [
        (STATUS_OFFER,     "🎉 Offers"),
        (STATUS_INTERVIEW, "🎤 Interviews"),
        (STATUS_APPLIED,   "📤 Applied"),
        (STATUS_REJECTED,  "❌ Rejected"),
    ]
    any_jobs = False
    for status, label in pipeline_order:
        jobs = rows_to_dicts(get_jobs(conn, status=status, limit=50))
        if not jobs:
            continue
        any_jobs = True
        st.markdown(f"### {label} &nbsp; `{len(jobs)}`")
        for job in jobs:
            job_card(conn, job, show_pdf=True)

    if not any_jobs:
        st.info("No applications submitted yet. Head to **✅ Ready** and mark jobs as applied.")


def tab_all(conn: sqlite3.Connection) -> None:
    f1, f2, f3 = st.columns([3, 2, 2])
    search     = f1.text_input("🔍 Search", placeholder="title or company…",
                                label_visibility="collapsed", key="all_search")
    status_sel = f2.selectbox("Status", ["All"] + [
        STATUS_NEW, STATUS_QUEUED, STATUS_APPROVED, STATUS_APPLIED,
        STATUS_INTERVIEW, STATUS_OFFER, STATUS_SKIPPED, STATUS_REJECTED,
    ], label_visibility="collapsed", key="all_status")
    min_score  = f3.slider("Min score", 0.0, 1.0, 0.3, 0.05, key="all_min")

    status_arg = None if status_sel == "All" else status_sel
    jobs = rows_to_dicts(get_jobs(conn, status=status_arg, min_score=min_score, limit=2000))

    if search:
        q = search.lower()
        jobs = [j for j in jobs if q in (j.get("title") or "").lower()
                or q in (j.get("company") or "").lower()]
        st.session_state["all_page"] = 0

    page_jobs, page, total_pages = _paginate(jobs, "all_page", PAGE_SIZE_ALL)

    st.caption(f"{len(jobs)} jobs · page {page + 1}/{total_pages}")

    # Table header
    h = st.columns([3, 1, 2, 1, 1, 1])
    for col, lbl in zip(h, ["Title / Company", "Score", "Status", "Date Applied", "Source", ""]):
        col.markdown(f"**{lbl}**")
    st.divider()

    for job in page_jobs:
        status     = job["status"]
        row_class  = STATUS_ROW_CLASS.get(status, "")
        date_app   = job.get("date_applied") or "—"
        # Truncate long dates to just YYYY-MM-DD
        if date_app and date_app != "—":
            date_app = date_app[:10]

        c = st.columns([3, 1, 2, 1, 1, 1])
        c[0].markdown(
            f'<div class="{row_class}"><strong>{job["title"]}</strong><br>'
            f'<span style="font-size:0.85rem;color:#666;">{job.get("company") or "N/A"}</span></div>',
            unsafe_allow_html=True,
        )
        c[1].markdown(
            f"{score_color(job['score'])} {job['score']:.0%}",
            help="AI relevance score vs. your profile",
        )
        c[2].markdown(status_pill(status), unsafe_allow_html=True)
        c[3].caption(date_app)
        c[4].caption(job.get("source", "?"))
        c[5].link_button("→", job.get("url", "#"))

    _pagination_controls(page, total_pages, len(jobs), "all_page", PAGE_SIZE_ALL)


# ── Import tab ─────────────────────────────────────────────────────────────────

def _insert_manual_job(conn: sqlite3.Connection, job: dict) -> tuple[bool, str]:
    """Insert a single manually-entered job. Returns (success, message)."""
    url   = (job.get("url")   or "").strip()
    title = (job.get("title") or "").strip()
    if not url or not title:
        return False, "URL and Job Title are required."

    try:
        conn.execute(
            """
            INSERT INTO jobs
                (title, company, location, url, source, score,
                 status, date_applied, notes, date_scraped)
            VALUES
                (:title, :company, :location, :url, :source, :score,
                 :status, :date_applied, :notes, datetime('now'))
            """,
            {
                "title":        title,
                "company":      (job.get("company")  or "").strip(),
                "location":     (job.get("location") or "").strip(),
                "url":          url,
                "source":       "manual",
                "score":        float(job.get("score", 1.0)),
                "status":       job.get("status", STATUS_APPLIED),
                "date_applied": job.get("date_applied") or None,
                "notes":        (job.get("notes") or "").strip() or None,
            },
        )
        conn.commit()
        return True, f"✅ Added: {title}"
    except sqlite3.IntegrityError:
        existing = conn.execute(
            "SELECT id, status FROM jobs WHERE url = ?", (url,)
        ).fetchone()
        if existing:
            update_status(
                conn, existing["id"], job.get("status", existing["status"]),
                date_applied=job.get("date_applied") or None,
                notes=(job.get("notes") or "").strip() or None,
            )
            return True, f"↩️ Updated existing entry: {title}"
        return False, "URL already exists and could not be updated."
    except Exception as e:
        return False, f"Error: {e}"


def tab_import(conn: sqlite3.Connection) -> None:
    # Empty state
    manual_count = conn.execute(
        "SELECT COUNT(*) FROM jobs WHERE source = 'manual'"
    ).fetchone()[0]

    if manual_count == 0:
        st.markdown("""
        <div style="text-align:center;padding:2rem;background:#f8f9ff;border-radius:12px;margin-bottom:1.5rem;">
            <div style="font-size:2.5rem;">📭</div>
            <h3 style="margin:0.5rem 0 0.25rem;">No manually imported jobs yet</h3>
            <p style="color:#666;margin:0;">
                Applied somewhere before this dashboard existed?<br>
                Add those jobs here so everything is tracked in one place.
            </p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.success(f"✅ {manual_count} job{'s' if manual_count != 1 else ''} imported manually — visible in the **📤 Applied** and **📋 All** tabs.")

    st.markdown("### 📥 Import Pre-Dashboard Applications")
    st.caption("Enter jobs you applied to before this dashboard existed.")

    manual_tab, csv_tab = st.tabs(["✍️ Manual Entry", "📂 CSV Bulk Upload"])

    # ── Manual entry ─────────────────────────────────────────────────────────────
    with manual_tab:
        col_a, col_b = st.columns(2)
        with col_a:
            imp_title    = st.text_input("Job Title *", placeholder="Software Engineer Intern")
            imp_company  = st.text_input("Company *",   placeholder="Google")
            imp_url      = st.text_input("Job Posting URL *", placeholder="https://...")
            imp_location = st.text_input("Location",    placeholder="Remote / New York, NY")
        with col_b:
            imp_status = st.selectbox(
                "Current Status *",
                [STATUS_APPLIED, STATUS_INTERVIEW, STATUS_OFFER, STATUS_REJECTED, STATUS_NEW],
                format_func=lambda s: {
                    STATUS_APPLIED:   "📤 Applied",
                    STATUS_INTERVIEW: "🎤 Interview",
                    STATUS_OFFER:     "🎉 Offer",
                    STATUS_REJECTED:  "❌ Rejected",
                    STATUS_NEW:       "🆕 New (discovered manually)",
                }.get(s, s),
            )
            imp_date = st.date_input(
                "Date Applied",
                value=date.today(),
                help="Leave as today if unknown.",
            )

        imp_notes = st.text_area(
            "Notes", placeholder="Recruiter name, referral source, interview stage…", height=80
        )

        if st.button("➕ Add Job", type="primary"):
            ok, msg = _insert_manual_job(conn, {
                "title":        imp_title,
                "company":      imp_company,
                "url":          imp_url,
                "status":       imp_status,
                "date_applied": str(imp_date) if imp_status != STATUS_NEW else None,
                "location":     imp_location,
                "notes":        imp_notes,
            })
            if ok:
                refresh(msg)
            else:
                st.error(msg)

    # ── CSV upload ────────────────────────────────────────────────────────────────
    with csv_tab:
        with st.expander("📋 Required CSV format", expanded=False):
            st.markdown("""
**Required columns:** `title`, `company`, `url`

**Optional columns:** `status`, `date_applied`, `location`, `notes`

**Valid status values:** `applied`, `interview`, `offer`, `rejected`, `new`

```
title,company,url,status,date_applied,location,notes
ML Intern,OpenAI,https://openai.com/careers/1,applied,2026-03-15,San Francisco CA,No response yet
Research Intern,DeepMind,https://deepmind.com/careers/2,interview,2026-03-20,Remote,Phone screen done
```
""")
            template_csv = "title,company,url,status,date_applied,location,notes\n"
            st.download_button(
                "⬇️ Download CSV Template",
                data=template_csv,
                file_name="import_template.csv",
                mime="text/csv",
            )

        uploaded = st.file_uploader(
            "Upload your CSV file",
            type=["csv"],
            help="UTF-8 encoded CSV — minimum columns: title, company, url",
        )

        if uploaded is not None:
            try:
                content = uploaded.read().decode("utf-8-sig")
                reader  = csv.DictReader(io.StringIO(content))
                rows    = list(reader)
            except Exception as e:
                st.error(f"Could not parse CSV: {e}")
                rows = []

            if rows:
                st.markdown(f"**Preview — {len(rows)} rows detected:**")
                preview_data = [
                    {
                        "Title":   r.get("title", ""),
                        "Company": r.get("company", ""),
                        "Status":  r.get("status", "applied"),
                        "Date":    r.get("date_applied", ""),
                        "URL":     (r.get("url", "") or "")[:50]
                                   + ("…" if len(r.get("url", "")) > 50 else ""),
                    }
                    for r in rows[:10]
                ]
                st.table(preview_data)
                if len(rows) > 10:
                    st.caption(f"… and {len(rows) - 10} more rows")

                valid_statuses = {
                    STATUS_APPLIED, STATUS_INTERVIEW, STATUS_OFFER,
                    STATUS_REJECTED, STATUS_NEW, STATUS_QUEUED,
                }

                if st.button(f"📥 Import {len(rows)} jobs", type="primary"):
                    success_count, fail_msgs = 0, []
                    for r in rows:
                        raw_status = (r.get("status") or "applied").strip().lower()
                        status = raw_status if raw_status in valid_statuses else STATUS_APPLIED
                        ok, msg = _insert_manual_job(conn, {
                            "title":        r.get("title", ""),
                            "company":      r.get("company", ""),
                            "url":          r.get("url", ""),
                            "status":       status,
                            "date_applied": r.get("date_applied") or None,
                            "location":     r.get("location", ""),
                            "notes":        r.get("notes", ""),
                        })
                        if ok:
                            success_count += 1
                        else:
                            fail_msgs.append(
                                f"• {r.get('title', '?')} @ {r.get('company', '?')}: {msg}"
                            )
                    if fail_msgs:
                        with st.expander(f"⚠️ {len(fail_msgs)} failed rows"):
                            st.text("\n".join(fail_msgs))
                    refresh(f"✅ Imported {success_count} / {len(rows)} jobs.")


# ── Keyboard navigation (j/k to move, a/s shortcuts) ───────────────────────────

_KEYBOARD_JS = """
<script>
(function() {
  // Only activate when not typing in an input / textarea
  let focusedIdx = -1;

  function getCards() {
    // Target the outermost bordered containers Streamlit renders for job cards
    return Array.from(
      document.querySelectorAll('[data-testid="stVerticalBlockBorderWrapper"]')
    );
  }

  function scrollToCard(idx) {
    const cards = getCards();
    if (idx < 0 || idx >= cards.length) return;
    cards[idx].scrollIntoView({ behavior: 'smooth', block: 'center' });
    cards.forEach((c, i) => {
      c.style.outline = i === idx ? '2px solid #1565c0' : '';
    });
    focusedIdx = idx;
  }

  document.addEventListener('keydown', function(e) {
    const tag = document.activeElement.tagName;
    if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return;

    const cards = getCards();
    if (e.key === 'j' || e.key === 'ArrowDown') {
      e.preventDefault();
      scrollToCard(Math.min(focusedIdx + 1, cards.length - 1));
    } else if (e.key === 'k' || e.key === 'ArrowUp') {
      e.preventDefault();
      scrollToCard(Math.max(focusedIdx - 1, 0));
    }
    // 'a' / 's' click the primary / skip button inside the focused card
    else if ((e.key === 'a' || e.key === 's') && focusedIdx >= 0) {
      e.preventDefault();
      const card = cards[focusedIdx];
      if (!card) return;
      const buttons = Array.from(card.querySelectorAll('button'));
      if (e.key === 'a') {
        // Primary button is always the first styled-primary one
        const primary = buttons.find(b => b.getAttribute('kind') === 'primaryFormSubmit'
                                       || b.classList.toString().includes('primary')
                                       || buttons[0]);
        if (primary) primary.click();
      } else {
        // Skip = button labelled "⏭ Skip"
        const skip = buttons.find(b => b.innerText.includes('Skip'));
        if (skip) skip.click();
      }
    }
  });
})();
</script>
"""


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    conn  = get_conn()
    stats = get_stats(conn)

    sidebar(conn)

    # Keyboard nav injection
    components.html(_KEYBOARD_JS, height=0)

    # ── Funnel header ─────────────────────────────────────────────────────────
    n_new      = stats.get(STATUS_NEW, 0)
    n_queued   = stats.get(STATUS_QUEUED, 0)
    n_approved = stats.get(STATUS_APPROVED, 0)
    n_applied  = stats.get(STATUS_APPLIED, 0)
    n_interview= stats.get(STATUS_INTERVIEW, 0)
    n_offer    = stats.get(STATUS_OFFER, 0)
    n_rejected = stats.get(STATUS_REJECTED, 0)
    n_tracked  = sum(stats.values())
    n_submitted = n_applied + n_interview + n_offer

    def _rate(num, den):
        return f"{num/den:.0%}" if den else "—"

    st.markdown(f"""
    <div class="funnel-header">
      <div>
        <h1>🎯 JobApply</h1>
        <p>Ishani Kathuria &nbsp;·&nbsp; Summer 2026 AI/ML Internship Search</p>
      </div>
      <div class="funnel-steps">
        <div class="funnel-step {'active' if n_new else ''}">
          🆕 {n_new} Discovered
        </div>
        <span class="funnel-arrow">▶</span>
        <div class="funnel-step {'active' if n_queued else ''}">
          ✅ {n_queued} Ready
          <span class="funnel-rate">({_rate(n_queued, n_new)})</span>
        </div>
        <span class="funnel-arrow">▶</span>
        <div class="funnel-step {'active' if n_submitted else ''}">
          📤 {n_submitted} Applied
          <span class="funnel-rate">({_rate(n_submitted, n_new)})</span>
        </div>
        <span class="funnel-arrow">▶</span>
        <div class="funnel-step {'active' if n_interview else ''}">
          🎤 {n_interview} Interview
          <span class="funnel-rate">({_rate(n_interview, n_submitted)})</span>
        </div>
        <span class="funnel-arrow">▶</span>
        <div class="funnel-step {'active' if n_offer else ''}">
          🎉 {n_offer} Offer
          <span class="funnel-rate">({_rate(n_offer, n_submitted)})</span>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Tabs ──────────────────────────────────────────────────────────────────
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        f"🆕 New ({n_new})",
        f"✅ Ready ({n_queued})",
        f"🚀 Approved ({n_approved})",
        f"📤 Applied ({n_submitted})",
        f"📋 All ({n_tracked})",
        "📥 Import",
    ])

    with tab1: tab_new(conn)
    with tab2: tab_queued(conn)
    with tab3: tab_approved(conn)
    with tab4: tab_applied(conn)
    with tab5: tab_all(conn)
    with tab6: tab_import(conn)


if __name__ == "__main__":
    main()
