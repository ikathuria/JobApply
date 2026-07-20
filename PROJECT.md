# JobApply — Project Tracker

> Living context map. Any LLM or human should be able to read this file alone and understand what the project is, how it's built, and where things are. **Keep it in sync** whenever the stack, structure, conventions, or status changes.

_Last updated: 2026-07-19_

---

## What it is

JobApply is a personal, fully-automated AI/ML job-search pipeline built for Ishani Kathuria (MS Applied AI @ Purdue Northwest, ex-AWS SDE, F-1 international student, graduating May 2027 / possibly Dec 2026). As of 2026-07-19 the primary target is **full-time new-grad AI/ML roles in the USA** (the Summer-2026 internship cycle is over); internships/co-ops stay in scope for CPT during the school year. It scrapes jobs from intern-list.com and newgrad-jobs.com, scores and filters them (AI/ML relevance, role type, recency, and **H-1B sponsorship history**), tailors a resume + cover letter per job using an LLM, and lets Ishani review everything in a React dashboard. It also drafts warm-referral and cold emails to recruiters and tracks outreach. A GitHub Actions workflow runs the scrape-score-tailor pipeline daily; a Render-hosted FastAPI server serves the dashboard.

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
├─ src/                          # all Python application packages (src layout)
│  ├─ scrapers/
│  │  ├─ jobright_minisite.py    # Shared requests client for jobright.ai JSON API (paging + normalize)
│  │  ├─ intern_list_scraper.py  # category "intern:us:ml_ai" + source label (uses jobright_minisite)
│  │  ├─ newgrad_jobs_scraper.py # category "newgrad:us:ml_ai" + source label (M12)
│  │  ├─ linkedin_scraper.py     # PAUSED — Playwright, not run in GHA
│  │  └─ handshake_scraper.py    # PAUSED — Playwright, not run in GHA
│  ├─ pipeline/
│  │  ├─ llm_client.py           # Unified Groq/Gemini/Anthropic interface
│  │  ├─ jd_fetcher.py           # Fetches full JD text from employer URL
│  │  ├─ resume_tailor.py        # LLM resume tailoring → JSON
│  │  ├─ cover_letter.py         # LLM cover letter generation
│  │  ├─ pdf_generator.py        # ReportLab PDF rendering
│  │  ├─ job_filter.py           # Keyword scoring + sponsorship + PhD/seniority filters
│  │  ├─ sponsorship.py          # H-1B sponsor lookup + score (M17)
│  │  ├─ jobright_enricher.py    # Enriches Jobright aggregator URLs
│  │  ├─ email_generator.py      # LLM cold email + referral ask generation (M14)
│  │  ├─ email_finder.py         # SMTP probe + Hunter.io email discovery (M15)
│  │  └─ email_sender.py         # Gmail SMTP send (M15)
│  ├─ tracker/
│  │  └─ tracker.py              # SQLite CRUD; jobs + recruiters + outreach + reminders (M19) tables
│  ├─ api/
│  │  ├─ main.py                 # FastAPI: all REST endpoints; serves apps/web/dist
│  │  └─ turso.py                # Turso HTTP bridge
│  └─ auto_apply/
│     ├─ apply_runner.py         # ATS detection + human-confirm loop
│     ├─ greenhouse_apply.py / linkedin_apply.py / lever_apply.py   # ✅ done
│     └─ (workday/ashby/smartrecruiters pending)
├─ apps/
│  └─ web/                       # React frontend (own package.json) — served by FastAPI
│     └─ src/
│        ├─ App.jsx              # Sidebar-driven screen routing
│        ├─ api.js               # fetch client for all /api endpoints
│        ├─ theme.js             # design tokens (warm paper/ink palette)
│        └─ components/
│           ├─ Sidebar.jsx       # nav (Dashboard/Jobs/Outreach/Timeline/Analytics/Settings)
│           ├─ DashboardView.jsx / JobsView.jsx / AnalyticsView.jsx
│           ├─ TimelineView.jsx  # Recruiting calendar + open-role counts + reminders (M19)
│           ├─ OutreachView.jsx  # Recruiter mgmt + composer + follow-up banner (M16)
│           ├─ SettingsView.jsx  # Settings (UI only until M7)
│           ├─ JobDrawer.jsx     # Full job detail panel + "Reach out"
│           └─ ui/index.jsx      # shared kit: Card, Btn, Input, Textarea, …
├─ config/
│  ├─ settings.yaml              # Runtime config (sources, scoring, filters, LLM)
│  ├─ profile.json               # Ishani's resume data (base for tailoring)
│  ├─ h1b_sponsors.json          # Curated known H-1B sponsors (M17)
│  └─ recruiting_calendar.json   # Curated per-company application windows (M19)
├─ scripts/                      # ops utilities (Turso reseed/pull, cleanup, enrich, refresh_h1b_sponsors)
├─ output/resumes/               # LLM-generated PDFs committed here for Render
├─ tests/                        # pytest unit tests
├─ .github/workflows/
│  ├─ ci.yml                     # lint (flake8) + pytest + web build on push/PR
│  └─ daily_tailor.yml           # Scheduled GHA pipeline
├─ main.py                       # CLI entry: --source, --tailor, --limit (bootstraps src/ onto sys.path)
├─ pyproject.toml                # packaging: src-layout packages, deps read from requirements.txt
├─ package.json                  # root delegator → apps/web npm scripts
├─ .flake8                       # flake8 config (pytest config lives in pyproject.toml)
├─ requirements.txt              # pinned deps (source of truth, read by pyproject)
├─ render.yaml
├─ CLAUDE.md                     # one-liner → PROJECT.md
└─ .env.example
```

---

## Conventions

- **All Python lives under `src/`** (src layout). Package names stay top-level — import as `from pipeline.x import y`, NOT `from src.pipeline...`. New scrapers → `src/scrapers/<source>_scraper.py` exposing `scrape() -> list[dict]`; new pipeline modules → `src/pipeline/<name>.py` (import `llm_client` for LLM calls); new API endpoints → `src/api/main.py`.
- **Tests** → `tests/test_<module>.py` (at repo root); use `pytest`; mock external calls (HTTP, SMTP, LLM) with `unittest.mock`
- **Packaging** → src-layout `pyproject.toml`; run `pip install -e .` so `uvicorn api.main:app`, pytest, and the scripts resolve packages from any CWD (CI/render/GHA all do this). Deps live in `requirements.txt` (pyproject reads them dynamically). CLI entry is `python main.py` (it bootstraps `src/` onto `sys.path`, so it also works without the install).
- **Path anchoring** → code that needs the repo root computes it from `__file__` (e.g. `api/main.py`: `ROOT = Path(__file__).parent.parent.parent`). `config/`, `output/`, `apps/web/dist`, and the local SQLite DB (`src/tracker/applications.db`) are all reached via `ROOT`.
- **Frontend** → lives in `apps/web/`; run via root npm scripts (`npm run dev|build`) which delegate with `--prefix apps/web`. FastAPI serves `apps/web/dist` in production.
- **Lint** → `flake8` (config in `.flake8`); pytest config in `pyproject.toml`. CI (`.github/workflows/ci.yml`) runs lint + pytest + web build on push/PR. Keep the whole tracked tree flake8-clean.
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
| 9. Interview Prep Section | ☐ planned | 2026-07-19 — upgraded from stub to a full section: LLM prep packs per interview (JD + company + profile), dedicated dashboard tab, stored + regenerable |
| 10. Email Notifications | ☐ todo | |
| 11. Production Hardening | ☐ todo | |
| 12. Scraper Pivot | ✅ done | LinkedIn/Handshake paused; intern-list + newgrad on jobright JSON API (browserless, ~1.9s/source) |
| 13. Recruiter Database | ✅ done | `recruiters` + `outreach` tables, CRUD + 8 API endpoints (25 tests) |
| 14. Cold Email Generator | ✅ done | LLM cold + referral drafts; `POST /api/outreach/draft` (33 tests) |
| 15. Email Discovery & Sending | ✅ done | email_finder (SMTP probe + Hunter), email_sender (Gmail), send endpoint + 7-day follow-up (45 tests) |
| 16. Outreach Dashboard UI | ✅ done | Outreach screen: recruiters, composer, send, follow-up banner, JobDrawer "Reach out" |
| 17. Visa-Sponsorship-History Filter | ✅ done | 2026-07-19 — boost known H-1B sponsors (~130 curated, token-subset match); opt-in require_sponsor hard filter; refresh script |
| 18. Retarget to Full-Time New-Grad | ✅ done | 2026-07-19 — broadened role gate (new-grad/entry-level/full-time + feed-source accept) + soft seniority penalty; internships/co-ops kept. New-grad roles scored 0.0 before, now surface |
| 19. Recruiting Timeline & Reminders | ✅ code done | 2026-07-19 — Timeline dashboard view: curated per-company app windows + live open-role counts + apply/reach-out reminders. Backend + tests green (68); ⚠ `apps/web/dist` needs a rebuild+commit (Node) to deploy |

**In progress now:** Strategic pivot (2026-07-19) — **M18 (retarget to full-time new-grad) and M19 (recruiting timeline & reminders) shipped**; **M17 (visa-sponsorship-history filter) is next**. Rationale: the Summer-2026 internship cycle produced 2 OAs / 1 interview from 500+ applications; the levers are targeting known H-1B sponsors, shifting to full-time new-grad roles (Ishani graduates May 2027), and not missing the new-grad application wave that opens Aug–Oct 2026 — not more application volume.
**Next up:** M17 (sponsorship-history filter), then M9 (interview-prep section — convert the interviews the pivot lands). Warm-referral outreach to ex-AWS/Google/MS/Uber contacts is timed to each company's window via the Timeline reminders. Optional: set `GMAIL_ADDRESS`/`GMAIL_APP_PASSWORD` for real sends; remaining pre-pivot milestones (M7, M8, M10, M11).

---

## Decision log

- 2026-07-19 — Interview Prep is now a full section (M9, planned) — the M17–M19 pivot is about landing more interviews; converting them is the next bottleneck (last cycle: 1 interview from 500+ apps). Upgraded the old thin "prep sheet button" stub into a dedicated dashboard section that generates + stores a tailored prep pack per interview (company/role snapshot, topics to review, behavioral/technical/system-design question banks with talking points from her real experience, questions to ask, logistics) from the JD + company + profile — grounded, never fabricated, same discipline as resume tailoring. Not built yet; planned after M17.
- 2026-07-19 — Recruiting Timeline & Reminders (M19) — for a May-2027 grad, the full-time new-grad cycle opens Aug–Oct 2026 (now) on rolling admissions, and Google's window is a tight ~2 weeks. Added a Timeline dashboard view combining a curated per-company application calendar (`config/recruiting_calendar.json`, cycle-specific + refreshable) with live open-role counts from the scraped `jobs` table, plus apply/reach-out reminders. Reach-out reminders fire on each company's application window (referrals help at application time), which revises the timing — but not the substance — of the earlier "defer warm outreach ~1 yr" decision. Curated windows are approximate (big tech is mostly rolling; hard per-req deadlines rarely publish); the live open-role counts give ground truth.
- 2026-07-19 — Strategic pivot to full-time new-grad AI/ML roles (M18) — Ishani graduates May 2027 (possibly Dec 2026); the Summer-2026 internship cycle is over, so full-time new-grad roles become the primary target. The `newgrad-jobs.com` scraper already existed, but `job_filter`'s role gate accepted only intern keywords and scored every new-grad role 0.0 — so they were scraped and silently discarded. Broadening the gate (with a seniority guard) unlocks them. Internships/co-ops kept for CPT during the school year — a re-prioritization, not a removal.
- 2026-07-19 — Added a visa-sponsorship-history filter (M17) — the biggest structural drag on the 500-application Summer-2026 cycle (2 OAs, 1 interview) was the "will you require sponsorship?" auto-reject. Scoring jobs by whether the company is a known H-1B sponsor (curated from public USCIS H-1B Employer Data Hub / MyVisaJobs data) tilts the odds better than raw volume. Soft/boost-only by default (unknown companies are not zeroed, since small/new employers may still sponsor); a strict `require_known_sponsor` flag is opt-in (wired from settings.yaml through run_pipeline). Kept as an offline JSON, not a live API call, so the daily path stays fast. Matching uses token-subset (not raw substring) so "Amazon Web Services" hits "Amazon" without "Metabolic Labs" hitting "Meta".
- 2026-07-19 — Outreach keeps both warm + cold email; warm-referral outreach deferred ~1 year — Ishani is on good terms with ex-AWS colleagues (some now at Google/Microsoft/Uber) but can't start work for ~a year, so she won't reach out yet. The module already supports both warm-referral and cold prompts; timing is a manual decision, not a code change. Referrals can be re-warmed a few months before availability.
- 2026-06-22 — LinkedIn + Handshake scrapers paused; replaced by newgrad-jobs.com — LinkedIn automation is fragile and risks account bans. Can be re-enabled in GHA by removing `if: false`.
- 2026-06-22 — intern-list + newgrad scrapers rewritten from Playwright to `requests` against jobright.ai's `swan/mini-sites/list` JSON API — ~1.9s vs 30–60s per source, no browser flakiness, and CI dropped the Chromium install (whole daily path is now browserless). Risk: undocumented internal endpoint could change; mitigated by it serving anonymously and a clean fallback to the git-tagged Playwright version if needed.
- 2026-06-22 — Added cold email outreach as a core feature (M13–M16) — job boards alone are insufficient; direct recruiter outreach dramatically increases response rates for internship searches.
- 2026-06-22 — Gmail SMTP chosen over OAuth2 for email sending — app password avoids the OAuth consent screen and is simpler for a personal tool; 500 sends/day is well within outreach volume.
- 2026-06-22 — All emails require user review before send — no auto-send to avoid mistakes; the system is a composer + tracker, not a blast tool.
- 2026-06-22 — `recruiters`/`outreach` FKs are declarative only; cascade-delete enforced in `delete_recruiter()` code — local sqlite doesn't set `foreign_keys=ON` and the Turso HTTP bridge skips PRAGMAs, so DB-level enforcement would behave differently per backend. Enforcing in code keeps both identical.
- 2026-06-23 — Repo restructured toward project-planner layout: frontend moved `web/` → `apps/web/`; added root `package.json` delegator, `pyproject.toml`, `CLAUDE.md`, and a `ci.yml` (lint+test+build).
- 2026-06-23 — Moved all Python packages under `src/` (src layout) to declutter the repo root. Coordinated path fixes: `api/main.py` ROOT anchor `+1` level + tracker-DB paths → `src/tracker`; `auto_apply` ROOT `+1`; `scripts/` `sys.path`/DB paths → `src/`; the local SQLite DB moved to `src/tracker/`. `pip install -e .` added to render/GHA/CI so `uvicorn api.main:app` and `python main.py` resolve packages. Package names stayed top-level (`api`, `pipeline`, …) so imports were unchanged. Dropped the `jobapply` console script — it required root `main.py` to be importable, which fights the src layout; `python main.py` (with a `sys.path` bootstrap) is the entry instead. Verified end-to-end: imports, pytest (46), `python main.py --stats`, live server (SPA+API 200 from `apps/web/dist`), npm build.
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
