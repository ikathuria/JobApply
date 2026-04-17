"""
JobApply Review Dashboard
Run: streamlit run dashboard/app.py

Tabs:
  - New Jobs       — discovered, not yet tailored
  - Ready to Apply — tailored resumes queued for review
  - Applied        — submitted applications
  - All Jobs       — full table view with filters
"""

import base64
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import streamlit as st

# Make sure imports resolve from project root
sys.path.insert(0, str(Path(__file__).parent.parent))

# Inject Streamlit secrets into env so pipeline modules pick them up
for _key in ("GOOGLE_API_KEY", "ANTHROPIC_API_KEY"):
    if _key in st.secrets:
        os.environ[_key] = st.secrets[_key]

# Streamlit Cloud mounts the repo under /mount/src — headed browser unavailable
IS_CLOUD = Path("/mount/src").exists()

from tracker.tracker import (
    init_db,
    get_jobs,
    get_stats,
    update_status,
    STATUS_NEW,
    STATUS_QUEUED,
    STATUS_SKIPPED,
    STATUS_APPLIED,
    STATUS_INTERVIEW,
    STATUS_REJECTED,
    STATUS_OFFER,
)

DB_PATH = Path(__file__).parent.parent / "tracker" / "applications.db"
OUTPUT_DIR = Path(__file__).parent.parent / "output" / "resumes"

st.set_page_config(
    page_title="JobApply Dashboard",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Helpers ───────────────────────────────────────────────────────────────────

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
    if score >= 0.7:
        return "🟢"
    if score >= 0.5:
        return "🟡"
    return "🔴"


def pdf_viewer(path: str) -> None:
    """Embed a PDF inline using an iframe."""
    p = Path(path)
    if not p.exists():
        st.warning(f"PDF not found: {path}")
        return
    b64 = base64.b64encode(p.read_bytes()).decode()
    st.markdown(
        f'<iframe src="data:application/pdf;base64,{b64}" '
        f'width="100%" height="600px" style="border:1px solid #ddd;border-radius:4px;"></iframe>',
        unsafe_allow_html=True,
    )


def open_file(path: str) -> None:
    if IS_CLOUD:
        return
    try:
        os.startfile(path)
    except AttributeError:
        subprocess.run(["xdg-open", path])


def status_badge(status: str) -> str:
    badges = {
        STATUS_NEW: "🆕 New",
        STATUS_QUEUED: "✅ Ready",
        STATUS_SKIPPED: "⏭ Skipped",
        STATUS_APPLIED: "📤 Applied",
        STATUS_INTERVIEW: "🎤 Interview",
        STATUS_REJECTED: "❌ Rejected",
        STATUS_OFFER: "🎉 Offer",
    }
    return badges.get(status, status)


# ── Sidebar ───────────────────────────────────────────────────────────────────

def sidebar(conn: sqlite3.Connection) -> None:
    st.sidebar.title("JobApply")
    st.sidebar.caption("AI Internship Hunter")

    stats = get_stats(conn)
    total = sum(stats.values())
    st.sidebar.markdown("### Pipeline Stats")
    cols = st.sidebar.columns(2)
    cols[0].metric("Total", total)
    cols[0].metric("New", stats.get(STATUS_NEW, 0))
    cols[0].metric("Applied", stats.get(STATUS_APPLIED, 0))
    cols[1].metric("Ready", stats.get(STATUS_QUEUED, 0))
    cols[1].metric("Interview", stats.get(STATUS_INTERVIEW, 0))
    cols[1].metric("Offer", stats.get(STATUS_OFFER, 0))

    st.sidebar.divider()
    st.sidebar.markdown("### Quick Actions")
    if not IS_CLOUD:
        if st.sidebar.button("Run Discovery (intern-list)", use_container_width=True):
            with st.spinner("Scraping intern-list.com..."):
                result = subprocess.run(
                    [sys.executable, "main.py", "--source", "intern_list"],
                    capture_output=True, text=True, cwd=Path(__file__).parent.parent,
                )
            if result.returncode == 0:
                st.sidebar.success("Discovery complete!")
            else:
                st.sidebar.error(f"Error:\n{result.stderr[-500:]}")
            refresh()
    else:
        st.sidebar.caption("Discovery runs automatically via GitHub Actions daily.")

    if st.sidebar.button("Tailor Top 10 Jobs", use_container_width=True):
        with st.spinner("Calling Claude API for tailoring..."):
            result = subprocess.run(
                [sys.executable, "main.py", "--tailor", "--limit", "10"],
                capture_output=True, text=True, cwd=Path(__file__).parent.parent,
            )
        if result.returncode == 0:
            st.sidebar.success("Tailoring complete!")
        else:
            st.sidebar.error(f"Error:\n{result.stderr[-500:]}")
        refresh()

    if st.sidebar.button("Refresh Data", use_container_width=True):
        refresh()


# ── Job card ──────────────────────────────────────────────────────────────────

def job_card(conn: sqlite3.Connection, job: dict, show_pdf: bool = True) -> None:
    score = job.get("score", 0.0)
    with st.container(border=True):
        col1, col2 = st.columns([6, 1])
        with col1:
            st.markdown(
                f"**{job['title']}** &nbsp; @ &nbsp; {job.get('company') or '_Unknown_'}"
            )
            st.caption(
                f"{score_color(score)} Score: {score:.2f} &nbsp;|&nbsp; "
                f"{status_badge(job['status'])} &nbsp;|&nbsp; "
                f"Source: {job.get('source', '?')} &nbsp;|&nbsp; "
                f"📍 {job.get('location') or 'USA'}"
            )
        with col2:
            st.link_button("Open Job", job.get("url", "#"), use_container_width=True)

        # Notes / description snippet
        if job.get("description"):
            with st.expander("Job description preview"):
                st.text(job["description"][:1500] + ("..." if len(job.get("description","")) > 1500 else ""))

        # PDF + actions for queued jobs
        if show_pdf and job.get("resume_path"):
            tabs = st.tabs(["Resume PDF", "Cover Letter"])
            with tabs[0]:
                if not IS_CLOUD:
                    col_a, _ = st.columns([1, 5])
                    col_a.button("Open PDF", key=f"open_r_{job['id']}",
                                 on_click=open_file, args=(job["resume_path"],))
                pdf_viewer(job["resume_path"])
            with tabs[1]:
                cl_txt_path = Path(job["resume_path"]).parent / "cover_letter.txt"
                cl_pdf_path = Path(job["resume_path"]).parent / "cover_letter.pdf"
                if cl_txt_path.exists():
                    letter = cl_txt_path.read_text(encoding="utf-8")
                    edited = st.text_area(
                        "Edit cover letter",
                        value=letter,
                        height=300,
                        key=f"cl_{job['id']}",
                    )
                    if st.button("Save edits", key=f"save_cl_{job['id']}"):
                        cl_txt_path.write_text(edited, encoding="utf-8")
                        st.success("Saved.")
                if cl_pdf_path.exists():
                    if not IS_CLOUD:
                        col_a2, _ = st.columns([1, 5])
                        col_a2.button("Open PDF", key=f"open_cl_{job['id']}",
                                      on_click=open_file, args=(str(cl_pdf_path),))
                    pdf_viewer(str(cl_pdf_path))

        # Action buttons
        st.divider()
        action_cols = st.columns(6)
        status = job["status"]

        if status == STATUS_QUEUED:
            if action_cols[0].button("Mark Applied", key=f"apply_{job['id']}", type="primary"):
                update_status(conn, job["id"], STATUS_APPLIED)
                refresh()
            if action_cols[1].button("Interview", key=f"interview_{job['id']}"):
                update_status(conn, job["id"], STATUS_INTERVIEW)
                refresh()

        if status == STATUS_NEW:
            if action_cols[0].button("Tailor This", key=f"tailor_{job['id']}", type="primary"):
                with st.spinner("Tailoring..."):
                    from pipeline.jd_fetcher import fetch_jd
                    from pipeline.resume_tailor import tailor_resume
                    from pipeline.cover_letter import generate_cover_letter
                    from pipeline.pdf_generator import generate_resume_pdf, generate_cover_letter_pdf
                    import re

                    jd_text = fetch_jd(job["url"])
                    if jd_text:
                        tailored = tailor_resume(job, jd_text)
                        if tailored:
                            slug = re.sub(r"[^a-z0-9_]", "", f"{job.get('company','')}_{job['title']}".lower().replace(" ", "_"))[:60]
                            job_dir = OUTPUT_DIR / slug
                            job_dir.mkdir(parents=True, exist_ok=True)
                            resume_path = job_dir / "resume.pdf"
                            cover_path = job_dir / "cover_letter.pdf"
                            letter_text = generate_cover_letter(job, jd_text, tailored.get("why_fit", ""))
                            generate_resume_pdf(tailored, resume_path)
                            if letter_text:
                                generate_cover_letter_pdf(letter_text, job, cover_path)
                                (job_dir / "cover_letter.txt").write_text(letter_text, encoding="utf-8")
                            update_status(conn, job["id"], STATUS_QUEUED, resume_path=str(resume_path))
                            st.success("Done! Reload to see resume.")
                        else:
                            st.error("Tailoring failed — check API key in .env")
                    else:
                        st.error("Could not fetch job description from URL.")
                refresh()

        if status not in (STATUS_SKIPPED, STATUS_REJECTED):
            if action_cols[2].button("Skip", key=f"skip_{job['id']}"):
                update_status(conn, job["id"], STATUS_SKIPPED)
                refresh()

        if status in (STATUS_APPLIED, STATUS_QUEUED):
            if action_cols[3].button("Rejected", key=f"reject_{job['id']}"):
                update_status(conn, job["id"], STATUS_REJECTED)
                refresh()
            if action_cols[4].button("Offer!", key=f"offer_{job['id']}"):
                update_status(conn, job["id"], STATUS_OFFER)
                refresh()

        # Notes field
        notes_key = f"notes_{job['id']}"
        new_notes = st.text_input(
            "Notes",
            value=job.get("notes") or "",
            placeholder="Add notes...",
            key=notes_key,
            label_visibility="collapsed",
        )
        if new_notes != (job.get("notes") or ""):
            update_status(conn, job["id"], job["status"], notes=new_notes)


# ── Tabs ──────────────────────────────────────────────────────────────────────

def tab_new(conn: sqlite3.Connection) -> None:
    st.subheader("New Jobs — Discovered, Not Yet Tailored")
    jobs = rows_to_dicts(get_jobs(conn, status=STATUS_NEW, limit=100))
    if not jobs:
        st.info("No new jobs. Run discovery from the sidebar.")
        return
    st.caption(f"{len(jobs)} jobs found")
    for job in jobs:
        job_card(conn, job, show_pdf=False)


def tab_queued(conn: sqlite3.Connection) -> None:
    st.subheader("Ready to Apply — Tailored Resumes Queued")
    jobs = rows_to_dicts(get_jobs(conn, status=STATUS_QUEUED, limit=100))
    if not jobs:
        st.info("No jobs queued. Run 'Tailor Top 10 Jobs' from the sidebar, or click 'Tailor This' on a new job.")
        return
    st.caption(f"{len(jobs)} jobs ready")
    for job in jobs:
        job_card(conn, job, show_pdf=True)


def tab_applied(conn: sqlite3.Connection) -> None:
    st.subheader("Applied")
    statuses = [STATUS_APPLIED, STATUS_INTERVIEW, STATUS_OFFER, STATUS_REJECTED]
    all_jobs = []
    for s in statuses:
        all_jobs.extend(rows_to_dicts(get_jobs(conn, status=s, limit=50)))
    all_jobs.sort(key=lambda j: j.get("date_applied") or "", reverse=True)
    if not all_jobs:
        st.info("No applications submitted yet.")
        return
    for job in all_jobs:
        job_card(conn, job, show_pdf=True)


def tab_all(conn: sqlite3.Connection) -> None:
    st.subheader("All Jobs")

    col1, col2, col3 = st.columns(3)
    status_filter = col1.selectbox(
        "Status",
        ["All", STATUS_NEW, STATUS_QUEUED, STATUS_APPLIED, STATUS_INTERVIEW,
         STATUS_SKIPPED, STATUS_REJECTED, STATUS_OFFER],
    )
    min_score = col2.slider("Min score", 0.0, 1.0, 0.3, 0.05)
    search = col3.text_input("Search title / company", placeholder="e.g. OpenAI, research...")

    status_arg = None if status_filter == "All" else status_filter
    jobs = rows_to_dicts(get_jobs(conn, status=status_arg, min_score=min_score, limit=500))

    if search:
        q = search.lower()
        jobs = [j for j in jobs if q in (j.get("title") or "").lower() or q in (j.get("company") or "").lower()]

    st.caption(f"{len(jobs)} jobs matching filters")

    # Compact table view
    for job in jobs:
        col_a, col_b, col_c, col_d = st.columns([3, 2, 1, 1])
        col_a.markdown(f"**{job['title']}** — {job.get('company') or 'N/A'}")
        col_b.caption(status_badge(job["status"]))
        col_c.caption(f"{score_color(job['score'])} {job['score']:.2f}")
        col_d.link_button("View", job.get("url", "#"))


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    conn = get_conn()
    sidebar(conn)

    st.title("JobApply — AI Internship Dashboard")
    st.caption("Ishani Kathuria | Summer 2026 AI/ML Internship Search")

    tab1, tab2, tab3, tab4 = st.tabs([
        "New Jobs",
        "Ready to Apply",
        "Applied / Tracking",
        "All Jobs",
    ])

    with tab1:
        tab_new(conn)
    with tab2:
        tab_queued(conn)
    with tab3:
        tab_applied(conn)
    with tab4:
        tab_all(conn)


if __name__ == "__main__":
    main()
