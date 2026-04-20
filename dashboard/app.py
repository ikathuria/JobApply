"""
JobApply Review Dashboard
Run: streamlit run dashboard/app.py
"""

import base64
import os
import re
import sqlite3
import subprocess
import sys
from pathlib import Path

import streamlit as st

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

st.set_page_config(
    page_title="JobApply",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ─────────────────────────────────────────────────────────────────

st.markdown("""
<style>
/* Header gradient */
.dash-header {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
    padding: 1.5rem 2rem;
    border-radius: 12px;
    margin-bottom: 1.5rem;
    color: white;
}
.dash-header h1 { margin: 0; font-size: 1.8rem; color: white; }
.dash-header p  { margin: 0.2rem 0 0; opacity: 0.75; font-size: 0.9rem; }

/* Score bar */
.score-bar-wrap { height: 6px; background: #e0e0e0; border-radius: 3px; }
.score-bar      { height: 6px; border-radius: 3px; }

/* Compact job row in All Jobs */
.job-row {
    display: flex; align-items: center; padding: 0.5rem 0;
    border-bottom: 1px solid #f0f0f0; gap: 1rem;
}

/* Status pill */
.pill {
    display: inline-block; padding: 2px 10px; border-radius: 20px;
    font-size: 0.75rem; font-weight: 600;
}
.pill-new      { background:#e3f2fd; color:#1565c0; }
.pill-queued   { background:#e8f5e9; color:#2e7d32; }
.pill-applied  { background:#fff3e0; color:#e65100; }
.pill-interview{ background:#f3e5f5; color:#6a1b9a; }
.pill-offer    { background:#e8f5e9; color:#1b5e20; }
.pill-rejected { background:#ffebee; color:#b71c1c; }
.pill-skipped  { background:#f5f5f5; color:#616161; }

/* Section label */
.section-label {
    font-size: 0.7rem; font-weight: 700; letter-spacing: 0.08em;
    text-transform: uppercase; color: #888; margin: 1rem 0 0.4rem;
}
</style>
""", unsafe_allow_html=True)


# ── Helpers ────────────────────────────────────────────────────────────────────

@st.cache_resource
def get_conn() -> sqlite3.Connection:
    conn = init_db(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def refresh():
    st.cache_resource.clear()
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
        f'<div class="score-bar-wrap">'
        f'<div class="score-bar" style="width:{pct}%;background:{color};"></div>'
        f'</div>'
    )


STATUS_META = {
    STATUS_NEW:       ("🆕", "New",       "pill-new"),
    STATUS_QUEUED:    ("✅", "Ready",     "pill-queued"),
    STATUS_APPROVED:  ("🚀", "Approved",  "pill-interview"),
    STATUS_SKIPPED:   ("⏭", "Skipped",   "pill-skipped"),
    STATUS_APPLIED:   ("📤", "Applied",   "pill-applied"),
    STATUS_INTERVIEW: ("🎤", "Interview", "pill-interview"),
    STATUS_REJECTED:  ("❌", "Rejected",  "pill-rejected"),
    STATUS_OFFER:     ("🎉", "Offer",     "pill-offer"),
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


def pdf_viewer(path: str) -> None:
    p = _resolve_path(path)
    if p is None:
        st.info("PDF not available on this environment — tailored locally only. Re-tailor here to generate it.")
        return
    data = p.read_bytes()
    b64  = base64.b64encode(data).decode()
    # <embed> works in Chrome where <iframe data:> is blocked
    st.markdown(
        f'<embed src="data:application/pdf;base64,{b64}" '
        f'type="application/pdf" width="100%" height="620px" '
        f'style="border:1px solid #e0e0e0;border-radius:8px;" />',
        unsafe_allow_html=True,
    )
    # Download button as reliable fallback
    st.download_button(
        "⬇️ Download PDF",
        data=data,
        file_name=p.name,
        mime="application/pdf",
        key=f"dl_{p}",
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
    with st.sidebar:
        st.markdown("## 🎯 JobApply")
        st.caption("AI/ML Internship Hunter · Summer 2026")
        st.divider()

        stats = get_stats(conn)
        total = sum(stats.values())

        # Funnel metrics
        st.markdown('<p class="section-label">Pipeline</p>', unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        c1.metric("Total",    total)
        c2.metric("Ready",    stats.get(STATUS_QUEUED, 0))
        c3.metric("Applied",  stats.get(STATUS_APPLIED, 0))

        c4, c5, c6 = st.columns(3)
        c4.metric("New",       stats.get(STATUS_NEW, 0))
        c5.metric("🚀 Approved", stats.get(STATUS_APPROVED, 0))
        c6.metric("Offer 🎉",  stats.get(STATUS_OFFER, 0))

        # Progress bar: applied / total
        if total:
            applied_pct = (stats.get(STATUS_APPLIED, 0) + stats.get(STATUS_INTERVIEW, 0) + stats.get(STATUS_OFFER, 0)) / total
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
                    st.success("Discovery complete!")
                else:
                    st.error(r.stderr[-400:])
                refresh()
        else:
            st.caption("🤖 Discovery runs daily via GitHub Actions.")

        n_tailor = st.number_input("Jobs to tailor", min_value=1, max_value=50, value=10, step=5)
        if st.button("✨ Tailor Jobs", use_container_width=True, type="primary"):
            with st.spinner(f"Tailoring {n_tailor} jobs..."):
                ok, out = _run_tailor(n_tailor)
            if ok:
                st.success(f"Done! Check Ready tab.")
            else:
                st.error(out[-400:])
            refresh()

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
                    st.success("Done! Screenshots saved to output/apply_screenshots/")
                else:
                    st.error(out[-400:])
                refresh()

        if st.button("🔄 Refresh", use_container_width=True):
            refresh()

        st.divider()
        st.caption("Powered by Gemini 2.5 Flash · ReportLab · Playwright")


# ── Job card ───────────────────────────────────────────────────────────────────

def job_card(conn: sqlite3.Connection, job: dict, show_pdf: bool = True) -> None:
    score = job.get("score", 0.0)
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

        # Score bar
        sc1, sc2 = st.columns([1, 8])
        sc1.caption(f"{score_color(score)} **{score:.0%}**")
        sc2.markdown(score_bar_html(score), unsafe_allow_html=True)
        sc2.empty()  # spacing

        # JD preview
        if job.get("description"):
            with st.expander("📄 Job description"):
                st.text(job["description"][:2000] + ("…" if len(job.get("description", "")) > 2000 else ""))

        # PDFs + dry-run screenshot
        if show_pdf and job.get("resume_path"):
            r_path    = _resolve_path(job["resume_path"]) or Path(job["resume_path"])
            cl_txt    = r_path.parent / "cover_letter.txt"
            cl_pdf    = r_path.parent / "cover_letter.pdf"
            shot_path = _screenshot_path(job)

            tab_labels = ["📄 Resume", "✉️ Cover Letter"]
            if shot_path:
                tab_labels.append("🖥️ Form Preview")

            tabs = st.tabs(tab_labels)

            with tabs[0]:
                pdf_viewer(str(r_path))

            with tabs[1]:
                if cl_txt.exists():
                    letter = cl_txt.read_text(encoding="utf-8")
                    edited = st.text_area("Cover letter", value=letter, height=280,
                                         key=f"cl_{job['id']}", label_visibility="collapsed")
                    c_save, _, __ = st.columns([1, 1, 4])
                    if c_save.button("💾 Save", key=f"save_cl_{job['id']}"):
                        cl_txt.write_text(edited, encoding="utf-8")
                        st.success("Saved.")
                elif IS_CLOUD:
                    st.info("Cover letter not available — re-tailor to generate it here.")
                pdf_viewer(str(cl_pdf))

            if shot_path:
                with tabs[2]:
                    st.caption(f"Dry-run screenshot — form as it would be submitted")
                    st.image(str(shot_path), use_container_width=True)

        # Action buttons
        st.markdown("---")
        btns = st.columns(6)

        if status == STATUS_NEW:
            if btns[0].button("✨ Tailor", key=f"tailor_{job['id']}", type="primary",
                              use_container_width=True):
                _tailor_single(conn, job)

        if status == STATUS_QUEUED:
            if btns[0].button("🚀 Approve", key=f"approve_{job['id']}", type="primary",
                              use_container_width=True, help="Approve for GHA auto-apply"):
                update_status(conn, job["id"], STATUS_APPROVED); refresh()
            if not IS_CLOUD:
                if btns[1].button("🔍 Dry Run", key=f"dry_{job['id']}",
                                  use_container_width=True, help="Fill form + screenshot, no submit"):
                    with st.spinner("Opening browser for dry run…"):
                        _run_dry_run(limit=1)
                    st.info("Done — check the 🖥️ Form Preview tab above.")
                    refresh()
            if btns[2].button("📤 Applied", key=f"apply_{job['id']}",
                              use_container_width=True, help="Mark as manually applied"):
                update_status(conn, job["id"], STATUS_APPLIED); refresh()
            if btns[3].button("🎤 Interview", key=f"int_{job['id']}",
                              use_container_width=True):
                update_status(conn, job["id"], STATUS_INTERVIEW); refresh()

        if status == STATUS_APPROVED:
            if btns[0].button("📤 Applied", key=f"apply2_{job['id']}", type="primary",
                              use_container_width=True):
                update_status(conn, job["id"], STATUS_APPLIED); refresh()
            if btns[1].button("↩ Unapprove", key=f"unapprove_{job['id']}",
                              use_container_width=True):
                update_status(conn, job["id"], STATUS_QUEUED); refresh()

        if status == STATUS_APPLIED:
            if btns[0].button("🎤 Interview", key=f"int2_{job['id']}", type="primary",
                              use_container_width=True):
                update_status(conn, job["id"], STATUS_INTERVIEW); refresh()

        if status == STATUS_INTERVIEW:
            if btns[0].button("🎉 Offer!", key=f"offer_{job['id']}", type="primary",
                              use_container_width=True):
                update_status(conn, job["id"], STATUS_OFFER); refresh()

        if status not in (STATUS_SKIPPED, STATUS_REJECTED, STATUS_OFFER):
            if btns[4].button("Skip", key=f"skip_{job['id']}", use_container_width=True):
                update_status(conn, job["id"], STATUS_SKIPPED); refresh()
            if btns[5].button("❌ Reject", key=f"rej_{job['id']}", use_container_width=True):
                update_status(conn, job["id"], STATUS_REJECTED); refresh()

        # Notes
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
        st.success("Done! Check the Ready tab.")
    refresh()


# ── Tabs ───────────────────────────────────────────────────────────────────────

def tab_new(conn: sqlite3.Connection) -> None:
    jobs = rows_to_dicts(get_jobs(conn, status=STATUS_NEW, limit=200))
    if not jobs:
        st.info("No new jobs yet. Run discovery from the sidebar or wait for the daily GitHub Action.")
        return

    # Filter bar
    f1, f2 = st.columns([3, 1])
    search = f1.text_input("🔍 Filter", placeholder="company, title…", label_visibility="collapsed")
    sort   = f2.selectbox("Sort", ["Score ↓", "Score ↑", "Company"], label_visibility="collapsed")

    if search:
        q = search.lower()
        jobs = [j for j in jobs if q in (j.get("title") or "").lower()
                or q in (j.get("company") or "").lower()]

    if sort == "Score ↓":   jobs.sort(key=lambda j: j["score"], reverse=True)
    elif sort == "Score ↑": jobs.sort(key=lambda j: j["score"])
    elif sort == "Company":  jobs.sort(key=lambda j: j.get("company") or "")

    st.caption(f"{len(jobs)} jobs · showing top results")

    for job in jobs:
        job_card(conn, job, show_pdf=False)


def tab_queued(conn: sqlite3.Connection) -> None:
    approved = rows_to_dicts(get_jobs(conn, status=STATUS_APPROVED, limit=100))
    queued   = rows_to_dicts(get_jobs(conn, status=STATUS_QUEUED, limit=100))

    if not approved and not queued:
        st.info("No jobs queued yet. Use **✨ Tailor Jobs** in the sidebar or click **✨ Tailor** on any new job.")
        return

    if approved:
        st.markdown(f"### 🚀 Approved for Auto-Apply &nbsp; `{len(approved)}`")
        st.caption("These will be submitted automatically by the GitHub Action. Review carefully before approving.")
        for job in approved:
            job_card(conn, job, show_pdf=True)

    if queued:
        st.markdown(f"### ✅ Ready — Awaiting Review &nbsp; `{len(queued)}`")
        st.caption("Click **🚀 Approve** to send to GitHub Actions, or **📤 Applied** if you applied manually.")
        for job in queued:
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
        st.info("No applications submitted yet. Head to **Ready to Apply** and mark jobs as applied.")


def tab_all(conn: sqlite3.Connection) -> None:
    f1, f2, f3 = st.columns([3, 2, 2])
    search      = f1.text_input("🔍 Search", placeholder="title or company…", label_visibility="collapsed")
    status_sel  = f2.selectbox("Status", ["All"] + [
        STATUS_NEW, STATUS_QUEUED, STATUS_APPLIED,
        STATUS_INTERVIEW, STATUS_OFFER, STATUS_SKIPPED, STATUS_REJECTED,
    ], label_visibility="collapsed")
    min_score   = f3.slider("Min score", 0.0, 1.0, 0.3, 0.05)

    status_arg = None if status_sel == "All" else status_sel
    jobs = rows_to_dicts(get_jobs(conn, status=status_arg, min_score=min_score, limit=500))

    if search:
        q = search.lower()
        jobs = [j for j in jobs if q in (j.get("title") or "").lower()
                or q in (j.get("company") or "").lower()]

    st.caption(f"{len(jobs)} jobs")

    # Header
    h = st.columns([4, 2, 1, 1, 1])
    for col, label in zip(h, ["Title / Company", "Status", "Score", "Source", ""]):
        col.markdown(f"**{label}**")
    st.divider()

    for job in jobs:
        c = st.columns([4, 2, 1, 1, 1])
        c[0].markdown(f"**{job['title']}**  \n{job.get('company') or 'N/A'}")
        c[1].markdown(status_pill(job["status"]), unsafe_allow_html=True)
        c[2].markdown(f"{score_color(job['score'])} {job['score']:.0%}")
        c[3].caption(job.get("source", "?"))
        c[4].link_button("→", job.get("url", "#"))


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    conn = get_conn()
    sidebar(conn)

    # Header
    stats = get_stats(conn)
    st.markdown(f"""
    <div class="dash-header">
        <h1>🎯 JobApply Dashboard</h1>
        <p>Ishani Kathuria &nbsp;·&nbsp; Summer 2026 AI/ML Internship Search &nbsp;·&nbsp;
           {sum(stats.values())} tracked &nbsp;·&nbsp;
           {stats.get(STATUS_QUEUED, 0)} ready &nbsp;·&nbsp;
           {stats.get(STATUS_APPLIED, 0) + stats.get(STATUS_INTERVIEW, 0) + stats.get(STATUS_OFFER, 0)} applied</p>
    </div>
    """, unsafe_allow_html=True)

    n_new      = stats.get(STATUS_NEW, 0)
    n_queued   = stats.get(STATUS_QUEUED, 0)
    n_approved = stats.get(STATUS_APPROVED, 0)
    n_applied  = stats.get(STATUS_APPLIED, 0) + stats.get(STATUS_INTERVIEW, 0) + stats.get(STATUS_OFFER, 0)
    n_total    = sum(stats.values())

    tab1, tab2, tab3, tab4 = st.tabs([
        f"🆕 New ({n_new})",
        f"✅ Ready ({n_queued + n_approved})",
        f"📤 Applied ({n_applied})",
        f"📋 All ({n_total})",
    ])

    with tab1: tab_new(conn)
    with tab2: tab_queued(conn)
    with tab3: tab_applied(conn)
    with tab4: tab_all(conn)


if __name__ == "__main__":
    main()
