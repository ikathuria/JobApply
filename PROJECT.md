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
| Scrapers | Python + requests | Python 3.12 | intern-list + newgrad-jobs hit jobright.ai's JSON API (browserless); LinkedIn + Handshake paused (Playwright, disabled) |
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
3. **FastAPI** (`api/main.py`) → REST API for jobs, recruiters, outreach; serves `apps/web/dist` in production
4. **React dashboard** → 6 views: Dashboard, Jobs, Analytics, Outreach, Settings, JobDrawer
5. **Cold email flow** → user adds recruiter in Outreach tab → LLM drafts email → user edits → send via Gmail SMTP → status tracked in `outreach` table

---

## Project structure

```
JobApply/
├─ scrapers/
│  ├─ jobright_minisite.py       # Shared requests client for jobright.ai JSON API (paging + normalize)
│  ├─ intern_list_scraper.py     # category "intern:us:ml_ai" + source label (uses jobright_minisite)
│  ├─ newgrad_jobs_scraper.py    # category "newgrad:us:ml_ai" + source label (M12)
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
│  ├─ __init__.py                # marks api as a package (for pyproject discovery)
│  ├─ main.py                    # FastAPI: all REST endpoints; serves apps/web/dist
│  └─ turso.py                   # Turso HTTP bridge
├─ auto_apply/
│  ├─ apply_runner.py            # ATS detection + human-confirm loop
│  ├─ greenhouse_apply.py        # ✅ done
│  ├─ linkedin_apply.py          # ✅ done
│  └─ lever_apply.py             # ✅ done
├─ apps/
│  └─ web/                       # React frontend (own package.json) — served by FastAPI
│     └─ src/
│        ├─ App.jsx              # Sidebar-driven screen routing
│        ├─ api.js               # fetch client for all /api endpoints
│        ├─ theme.js             # design tokens (warm paper/ink palette)
│        └─ components/
│           ├─ Sidebar.jsx       # nav (Dashboard/Jobs/Outreach/Analytics/Settings)
│           ├─ DashboardView.jsx # Hero stats + focus cards
│           ├─ JobsView.jsx      # Tabbed by status, bulk update
│           ├─ AnalyticsView.jsx # Funnel + Sankey
│           ├─ OutreachView.jsx  # Recruiter mgmt + composer + follow-up banner (M16)
│           ├─ SettingsView.jsx  # Settings (UI only until M7)
│           ├─ JobDrawer.jsx     # Full job detail panel + "Reach out"
│           └─ ui/index.jsx      # shared kit: Card, Btn, Input, Textarea, …
├─ config/
│  ├─ settings.yaml              # Runtime config (sources, scoring, LLM)
│  └─ profile.json               # Ishani's resume data (base for tailoring)
├─ output/resumes/               # LLM-generated PDFs committed here for Render
├─ tests/                        # pytest unit tests
├─ .github/workflows/
│  ├─ ci.yml                     # lint (flake8) + pytest + web build on push/PR
│  └─ daily_tailor.yml           # Scheduled GHA pipeline
├─ main.py                       # CLI entry: --source, --tailor, --limit
├─ pyproject.toml                # packaging: declares packages, deps (from requirements.txt), `jobapply` script
├─ package.json                  # root delegator → apps/web npm scripts
├─ setup.cfg                     # flake8 config
├─ requirements.txt              # pinned deps (source of truth, read by pyproject)
├─ render.yaml
├─ CLAUDE.md                     # one-liner → PROJECT.md
└─ .env.example
```

---

## Conventions

- **New scrapers** → `scrapers/<source>_scraper.py`; must expose a `scrape() -> list[dict]` function returning dicts with keys `title, company, url, location, date_posted, source`
- **New pipeline modules** → `pipeline/<name>.py`; import `llm_client` for any LLM calls
- **New API endpoints** → add to `api/main.py`; follow existing route naming (`GET /api/...`, `POST /api/...`, `PATCH /api/...`)
- **Tests** → `tests/test_<module>.py`; use `pytest`; mock external calls (HTTP, SMTP, LLM) with `unittest.mock`
- **Packaging** → flat-layout `pyproject.toml`; Python packages stay at repo root (imports unchanged). `pip install -e .` installs them + the `jobapply` console script. Deps live in `requirements.txt` (pyproject reads them dynamically).
- **Frontend** → lives in `apps/web/`; run via root npm scripts (`npm run dev|build`) which delegate with `--prefix apps/web`. FastAPI serves `apps/web/dist` in production.
- **Lint** → `flake8` (config in `setup.cfg`); CI (`.github/workflows/ci.yml`) runs lint + pytest + web build on push/PR. Keep the whole tracked tree flake8-clean.
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
| 12. Scraper Pivot | ✅ done | LinkedIn/Handshake paused; intern-list + newgrad on jobright JSON API (browserless, ~1.9s/source) |
| 13. Recruiter Database | ✅ done | `recruiters` + `outreach` tables, CRUD + 8 API endpoints (25 tests) |
| 14. Cold Email Generator | ✅ done | LLM cold + referral drafts; `POST /api/outreach/draft` (33 tests) |
| 15. Email Discovery & Sending | ✅ done | email_finder (SMTP probe + Hunter), email_sender (Gmail), send endpoint + 7-day follow-up (45 tests) |
| 16. Outreach Dashboard UI | ✅ done | Outreach screen: recruiters, composer, send, follow-up banner, JobDrawer "Reach out" |

**In progress now:** M16 complete — Outreach dashboard UI done. **All planned outreach milestones (M12–M16) shipped.**
**Next up:** Optional — set `GMAIL_ADDRESS`/`GMAIL_APP_PASSWORD` to enable real sends; remaining pre-pivot milestones (M7–M11) if desired.

---

## Decision log

- 2026-06-22 — LinkedIn + Handshake scrapers paused; replaced by newgrad-jobs.com — LinkedIn automation is fragile and risks account bans. Can be re-enabled in GHA by removing `if: false`.
- 2026-06-22 — intern-list + newgrad scrapers rewritten from Playwright to `requests` against jobright.ai's `swan/mini-sites/list` JSON API — ~1.9s vs 30–60s per source, no browser flakiness, and CI dropped the Chromium install (whole daily path is now browserless). Risk: undocumented internal endpoint could change; mitigated by it serving anonymously and a clean fallback to the git-tagged Playwright version if needed.
- 2026-06-22 — Added cold email outreach as a core feature (M13–M16) — job boards alone are insufficient; direct recruiter outreach dramatically increases response rates for internship searches.
- 2026-06-22 — Gmail SMTP chosen over OAuth2 for email sending — app password avoids the OAuth consent screen and is simpler for a personal tool; 500 sends/day is well within outreach volume.
- 2026-06-22 — All emails require user review before send — no auto-send to avoid mistakes; the system is a composer + tracker, not a blast tool.
- 2026-06-22 — `recruiters`/`outreach` FKs are declarative only; cascade-delete enforced in `delete_recruiter()` code — local sqlite doesn't set `foreign_keys=ON` and the Turso HTTP bridge skips PRAGMAs, so DB-level enforcement would behave differently per backend. Enforcing in code keeps both identical.
- 2026-06-23 — Repo restructured toward project-planner layout: frontend moved `web/` → `apps/web/`; added root `package.json` delegator, `pyproject.toml` (flat-layout packaging), `CLAUDE.md`, and a `ci.yml` (lint+test+build). **Python kept flat at repo root (not moved to `src/`)** — `api/main.py` anchors `ROOT` via `__file__` to find `apps/web/dist` + `output/`, and the deploy entry points (`uvicorn api.main:app`, `python main.py`) run from root; a `src/` move would force coordinated path surgery + `pip install -e .` everywhere for purely cosmetic gain. Flat-layout `pyproject.toml` delivers the packaging benefits with zero import/path churn.
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
