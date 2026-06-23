# JobApply — Project Tracker

> Living context map. Any LLM or human should be able to read this file alone and understand what the project is, how it's built, and where things are. **Keep it in sync** whenever the stack, structure, conventions, or status changes.

_Last updated: 2026-06-22_

---

## What it is

JobApply is a personal, fully-automated AI/ML internship search pipeline built for Ishani Kathuria (MS AI @ Purdue, ex-AWS SDE, targeting Summer 2026 USA internships). It scrapes jobs from intern-list.com and newgrad-jobs.com, scores and filters them, tailors a resume + cover letter per job using an LLM, and lets Ishani review everything in a React dashboard. It also sends cold emails to recruiters and tracks outreach. A GitHub Actions workflow runs the scrape-score-tailor pipeline daily; a Render-hosted FastAPI server serves the dashboard.

---

## Stack

| Layer | Choice | Version | Notes |
|---|---|---|---|
| Scrapers | Python + Playwright | Python 3.12 | intern-list + newgrad-jobs scroll a virtualized jobright.ai embed table; LinkedIn + Handshake paused |
| LLM / Tailoring | Groq (llama-3.1-8b-instant) | Groq API | Free tier; Gemini + Claude are fallbacks via `pipeline/llm_client.py` |
| Email | Gmail SMTP (smtplib) + optional Hunter.io | — | App password auth; 500 sends/day free |
| PDF generation | ReportLab | latest | Local, no API |
| Backend API | FastAPI + Uvicorn | latest | Serves React build + REST API |
| Database | SQLite (local/dev) + Turso libsql (cloud) | — | WAL local; Turso for GHA + Render |
| Frontend | React 18 + Vite | 18 / 5.x | No router/CSS framework; 6 views incl. Outreach |
| CI/CD | GitHub Actions | — | Daily at 21:00 UTC; `workflow_dispatch` for manual runs |
| Hosting | Render free tier | — | Single web service: FastAPI serves built React dist |
| ATS automation | Playwright | latest | Greenhouse, LinkedIn Easy Apply, Lever handlers done |

---

## Architecture

1. **GHA daily workflow** → runs `main.py --source intern_list` + `main.py --source newgrad_jobs` → jobs scored + inserted into Turso DB
2. **`main.py --tailor`** → fetches JDs → LLM tailors resume + cover letter → ReportLab generates PDFs → committed to `output/resumes/`
3. **FastAPI** (`api/main.py`) → REST API for jobs, recruiters, outreach; serves `web/dist` in production
4. **React dashboard** → 6 views: Dashboard, Jobs, Analytics, Outreach, Settings, JobDrawer
5. **Cold email flow** → user adds recruiter in Outreach tab → LLM drafts email → user edits → send via Gmail SMTP → status tracked in `outreach` table

---

## Project structure

```
JobApply/
├─ scrapers/
│  ├─ jobright_minisite.py       # Shared Playwright scroll/harvest for jobright.ai embed tables
│  ├─ intern_list_scraper.py     # intern-list.com embed URL + source label (uses jobright_minisite)
│  ├─ newgrad_jobs_scraper.py    # newgrad-jobs.com embed URL + source label (M12)
│  ├─ linkedin_scraper.py        # PAUSED — Playwright, not run in GHA
│  └─ handshake_scraper.py       # PAUSED — Playwright, not run in GHA
├─ pipeline/
│  ├─ llm_client.py              # Unified Groq/Gemini/Anthropic interface
│  ├─ jd_fetcher.py              # Fetches full JD text from employer URL
│  ├─ resume_tailor.py           # LLM resume tailoring → JSON
│  ├─ cover_letter.py            # LLM cover letter generation
│  ├─ pdf_generator.py           # ReportLab PDF rendering
│  ├─ job_filter.py              # Keyword scoring + sponsorship filter
│  ├─ jobright_enricher.py       # Enriches Jobright aggregator URLs
│  ├─ email_generator.py         # LLM cold email + referral ask generation (M14)
│  ├─ email_finder.py            # SMTP probe + Hunter.io email discovery (M15)
│  └─ email_sender.py            # Gmail SMTP send (M15)
├─ tracker/
│  ├─ tracker.py                 # SQLite CRUD; jobs + recruiters + outreach tables
│  └─ ...
├─ api/
│  └─ main.py                    # FastAPI: all REST endpoints; serves web/dist
├─ auto_apply/
│  ├─ apply_runner.py            # ATS detection + human-confirm loop
│  ├─ greenhouse_apply.py        # ✅ done
│  ├─ linkedin_apply.py          # ✅ done
│  └─ lever_apply.py             # ✅ done
├─ web/
│  └─ src/
│     ├─ App.jsx                 # Tab bar + routing
│     ├─ DashboardView.jsx       # Hero stats + focus cards
│     ├─ JobsView.jsx            # Tabbed by status, bulk update
│     ├─ AnalyticsView.jsx       # Funnel + Sankey
│     ├─ OutreachView.jsx        # Recruiter mgmt + email composer (M16)
│     ├─ SettingsView.jsx        # Settings (UI only until M7)
│     └─ JobDrawer.jsx           # Full job detail panel
├─ config/
│  ├─ settings.yaml              # Runtime config (sources, scoring, LLM)
│  └─ profile.json               # Ishani's resume data (base for tailoring)
├─ output/resumes/               # LLM-generated PDFs committed here for Render
├─ tests/                        # pytest unit tests
├─ .github/workflows/
│  └─ daily_tailor.yml           # Scheduled GHA pipeline
├─ main.py                       # CLI entry: --source, --tailor, --limit
├─ requirements.txt
├─ render.yaml
└─ .env.example
```

---

## Conventions

- **New scrapers** → `scrapers/<source>_scraper.py`; must expose a `scrape() -> list[dict]` function returning dicts with keys `title, company, url, location, date_posted, source`
- **New pipeline modules** → `pipeline/<name>.py`; import `llm_client` for any LLM calls
- **New API endpoints** → add to `api/main.py`; follow existing route naming (`GET /api/...`, `POST /api/...`, `PATCH /api/...`)
- **Tests** → `tests/test_<module>.py`; use `pytest`; mock external calls (HTTP, SMTP, LLM) with `unittest.mock`
- **Before coding against any library**: fetch its latest official docs — never code APIs from memory

---

## Current status

| Milestone | Status | Notes |
|---|---|---|
| 1. Scaffold | ✅ done | |
| 2. Discovery Pipeline | ✅ done | intern-list, LinkedIn (paused), Handshake (paused) |
| 3. Resume Tailoring | ✅ done | Groq default; 50+ PDFs generated |
| 4. Review Dashboard | ✅ done | 5 views in React |
| 5. CI/CD Automation | ✅ done | Daily GHA at 4 PM CDT |
| 6. Auto-Apply | ◐ partial | Greenhouse/LinkedIn/Lever done; Workday/Ashby/SmartRecruiters pending |
| 7. Settings Persistence | ☐ todo | |
| 8. Import Jobs UI | ☐ todo | |
| 9. Interview Prep Module | ☐ todo | |
| 10. Email Notifications | ☐ todo | |
| 11. Production Hardening | ☐ todo | |
| 12. Scraper Pivot | ✅ done | LinkedIn/Handshake paused; newgrad-jobs.com live (22 jobs verified) |
| 13. Recruiter Database | ☐ todo | `recruiters` + `outreach` tables + CRUD API |
| 14. Cold Email Generator | ☐ todo | LLM draft: cold + referral variants |
| 15. Email Discovery & Sending | ☐ todo | SMTP probe + Hunter.io + Gmail send |
| 16. Outreach Dashboard UI | ☐ todo | New Outreach tab in React |

**In progress now:** M12 complete — scraper pivot done
**Next up:** M13 — Recruiter & Outreach Database (`recruiters` + `outreach` tables + CRUD API)

---

## Decision log

- 2026-06-22 — LinkedIn + Handshake scrapers paused; replaced by newgrad-jobs.com — LinkedIn automation is fragile and risks account bans; newgrad-jobs.com is a cleaner HTML target. Can be re-enabled in GHA by removing `if: false`.
- 2026-06-22 — Added cold email outreach as a core feature (M13–M16) — job boards alone are insufficient; direct recruiter outreach dramatically increases response rates for internship searches.
- 2026-06-22 — Gmail SMTP chosen over OAuth2 for email sending — app password avoids the OAuth consent screen and is simpler for a personal tool; 500 sends/day is well within outreach volume.
- 2026-06-22 — All emails require user review before send — no auto-send to avoid mistakes; the system is a composer + tracker, not a blast tool.
- Earlier — LLM provider default changed from Gemini to Groq (llama-3.1-8b-instant) — Groq free tier has no daily quota; Gemini was hitting rate limits during heavy tailoring days.
- Earlier — PDFs committed to git for Render access — Render free tier has no persistent disk; committing output/ is the simplest path. Revisit if output/ exceeds 100MB.

---

## Glossary

- **tailoring** — LLM rewrites Ishani's resume bullets + summary to match a specific job description; output is a JSON that feeds the PDF generator
- **queued** — job status: tailored PDF generated, ready for Ishani to review and approve for application
- **approved** — job status: Ishani has reviewed and approved; next step is auto-apply or manual apply
- **cold email** — outreach to a recruiter or HR person at a company, initiated without a prior connection
- **referral ask** — outreach to a current employee at the target company, asking them to refer Ishani to the hiring team
- **Turso** — cloud-hosted SQLite-compatible database used by GHA and Render (since neither has persistent local disk); `api/turso.py` bridges the `libsql` protocol
- **Groq** — free LLM inference provider; `llama-3.1-8b-instant` is the default model
