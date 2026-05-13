# JobApply

> Fully-automated AI internship pipeline: scrape → score → tailor resume per JD → review in React dashboard → auto-fill ATS forms → track outcomes.

---

## Viability Summary

| | |
|---|---|
| **Market** | Personal tool — no commercial intent; built for Ishani's Summer 2026 AI/ML internship search |
| **Feasibility** | Medium — core pipeline is complete; remaining work is polish, ATS coverage, and quality |
| **Free to build** | Mostly — Render free tier for hosting; Groq free tier for LLM; Turso free tier for cloud DB |
| **Monetization** | Portfolio project |

---

## Tech Stack

| Layer | Choice | Reason |
|---|---|---|
| Scrapers | Python + BeautifulSoup + Playwright | intern-list (HTML scrape), LinkedIn & Handshake (browser automation) |
| LLM / Tailoring | Llama 3.1 8B via Groq (default) / Gemini / Claude Sonnet (fallbacks) | Groq free tier (console.groq.com); switchable via `pipeline/llm_client.py` |
| PDF generation | ReportLab | local, no API dependency |
| Backend API | FastAPI + Uvicorn | full CRUD; serves React build in production |
| Database | SQLite (local) + Turso libsql (cloud) | WAL local dev; Turso for GHA + Render persistence |
| Frontend | React 18 + Vite (no router, no CSS framework) | minimal deps; 5 views: Dashboard, Jobs, Analytics, Settings, JobDrawer |
| CI/CD | GitHub Actions (`.github/workflows/daily_tailor.yml`) | runs at 4 PM CDT — discovers, enriches, tailors, commits PDFs |
| Hosting | Render free tier (`render.yaml`) | single web service: FastAPI serves built React dist |
| ATS automation | Playwright (auto_apply/) | Greenhouse, LinkedIn Easy Apply, Lever have full handlers |

---

## Environment Variables

```
# Required for tailoring
GROQ_API_KEY=           # Groq API key — console.groq.com (free)
GOOGLE_API_KEY=         # Gemini API key — aistudio.google.com (free, fallback)
ANTHROPIC_API_KEY=      # Claude fallback — console.anthropic.com

# Required for LinkedIn scraper + LinkedIn auto-apply
LINKEDIN_EMAIL=
LINKEDIN_PASSWORD=

# Required for Handshake scraper
HANDSHAKE_EMAIL=
HANDSHAKE_PASSWORD=

# Optional — Jobright enricher
JOBRIGHT_EMAIL=
JOBRIGHT_PASSWORD=

# Optional — Turso cloud DB (needed for GHA + Render persistence)
TURSO_DATABASE_URL=     # from Turso dashboard
TURSO_AUTH_TOKEN=       # from Turso dashboard → Generate token
```

---

## Project Status

The pipeline is **production-ready and running daily**. The sections below track what is complete and what remains.

---

## Milestone 1: Scaffold ✅
**Goal:** Repo + deps + env wired up.

- [x] Python package structure (`scrapers/`, `pipeline/`, `tracker/`, `auto_apply/`, `api/`, `web/`)
- [x] `requirements.txt` with all deps (playwright, fastapi, uvicorn, reportlab, google-genai, anthropic, pyyaml, etc.)
- [x] `.env.example` committed
- [x] `config/settings.yaml` — all runtime config (sources, scoring weights, LLM provider)
- [x] `config/profile.json` — Ishani's full resume data (base for all tailoring)

---

## Milestone 2: Discovery Pipeline ✅
**Goal:** Daily scraping from 3 sources → scored jobs in SQLite.

- [x] `scrapers/intern_list_scraper.py` — BeautifulSoup scraper for intern-list.com
- [x] `scrapers/linkedin_scraper.py` — Playwright scraper (Easy Apply filter, up to 60 jobs)
- [x] `scrapers/handshake_scraper.py` — Playwright scraper (5 queries, up to 80 jobs)
- [x] `pipeline/job_filter.py` — keyword scoring (keyword_match 40%, role_relevance 30%, recency 20%, sponsorship_friendly 10%); auto-excludes "no sponsorship" jobs
- [x] `pipeline/jobright_enricher.py` — enriches Jobright aggregator URLs to get employer URL, salary, description
- [x] `tracker/tracker.py` — SQLite CRUD with WAL mode; 9 statuses: new → queued → approved → applied → oa → interview → offer / rejected / skipped
- [x] `api/turso.py` — Turso libsql bridge (seed from SQLite on first deploy)
- [x] `main.py --source <intern_list|linkedin|handshake>` discovery + filter flow

---

## Milestone 3: Resume Tailoring Pipeline ✅
**Goal:** LLM-tailored resume + cover letter PDFs per job, output to `output/resumes/<slug>/`.

- [x] `pipeline/jd_fetcher.py` — fetches full JD text from employer URL
- [x] `pipeline/llm_client.py` — unified Groq / Gemini / Anthropic interface; Groq is default (free tier, OpenAI-compatible API)
- [x] `pipeline/resume_tailor.py` — system prompt includes full profile; returns JSON (summary, experience, projects, skills, why_fit); never fabricates
- [x] `pipeline/cover_letter.py` — generates personalized cover letter from JD + why_fit hook
- [x] `pipeline/pdf_generator.py` — ReportLab renders resume + cover letter PDFs
- [x] `main.py --tailor --limit N` flow (fetch JD → tailor → cover letter → PDF → mark queued)
- [x] 50+ tailored resumes committed in `output/resumes/`

---

## Milestone 4: Review Dashboard ✅
**Goal:** React UI to review tailored jobs, update statuses, read PDFs, and trigger tailoring.

- [x] **FastAPI backend** (`api/main.py`): `/api/stats`, `/api/focus`, `/api/jobs`, `/api/jobs/{id}`, `PATCH /api/jobs/{id}`, `POST /api/jobs/bulk`, `POST /api/jobs/{id}/tailor`, `/api/jobs/{id}/resume`, `/api/jobs/{id}/cover_letter`, `/api/jobs/{id}/cover_letter.pdf`, `PATCH /api/jobs/{id}/cover_letter`, `POST /api/jobs/import`
- [x] **JobDrawer** — full job detail panel: status dropdown, notes, dates, recruiter, salary, interview date, follow-up, inline cover letter edit, resume PDF preview, tailor button
- [x] **DashboardView** — hero stats banner, focus task cards (today's priority), top-match cards
- [x] **JobsView** — tabbed by status, search/filter, bulk status update, job row with score chip
- [x] **AnalyticsView** — application funnel, conversion rates, rejection by stage, Sankey pipeline flow SVG
- [x] **SettingsView** — profile fields, API key fields, source toggles, behavior toggles (UI only — not persisted)
- [x] Dark / light mode with CSS custom properties
- [x] FastAPI serves built `web/dist` in production

---

## Milestone 5: CI/CD Automation ✅
**Goal:** Fully automated daily pipeline via GitHub Actions.

- [x] `.github/workflows/daily_tailor.yml` — runs at 21:00 UTC (4 PM CDT) daily
- [x] Steps: discover all 3 sources (continue-on-error) → enrich Jobright jobs → tailor top 50 → commit PDFs
- [x] Turso env vars passed as GHA secrets; DB state lives in cloud
- [x] `workflow_dispatch` for manual runs with `limit` and `sources` overrides

---

## Milestone 6: Auto-Apply ✅ (partial)
**Goal:** Playwright auto-fill ATS forms for approved jobs; human confirms each submit.

- [x] `auto_apply/apply_runner.py` — loads approved jobs, detects ATS by URL pattern, fills form, screenshots, prompts for confirm/skip/quit
- [x] `auto_apply/greenhouse_apply.py` — fills all standard Greenhouse fields; handles custom screening questions (sponsorship, relocation, graduation, GPA)
- [x] `auto_apply/linkedin_apply.py` — LinkedIn Easy Apply form handler
- [x] `auto_apply/lever_apply.py` — Lever form handler
- [x] Dry-run mode (`--dry-run`): fills form + screenshot, never submits
- [ ] **Workday handler** — most common enterprise ATS; currently opens browser for manual fill — Done when: `auto_apply/workday_apply.py` can fill the multi-step Workday form and detect the submit step
- [ ] **Ashby handler** — common at AI startups — Done when: `auto_apply/ashby_apply.py` fills name/email/resume/cover letter on `jobs.ashbyhq.com` forms
- [ ] **SmartRecruiters handler** — Done when: `auto_apply/smartrecruiters_apply.py` fills basic info fields

---

## Milestone 7: Settings Persistence
**Goal:** Settings saved in the UI actually take effect.

- [ ] Add `GET /api/settings` + `POST /api/settings` endpoints in `api/main.py` — Done when: endpoints return and accept a JSON object matching `config/settings.yaml` keys
- [ ] Persist settings to `config/settings.yaml` on POST (read → merge → write) — Done when: changing min score in UI and reloading reflects in scoring
- [ ] Wire `SettingsView.jsx` save button to `POST /api/settings` — Done when: clicking Save shows success toast and the new values are returned by GET on reload
- [ ] Reload `_config_cache` in `llm_client.py` after settings change — Done when: switching LLM provider from the UI takes effect on next tailor run

---

## Milestone 8: Import Jobs UI
**Goal:** Manually add a job (with applied date) from the dashboard — for jobs submitted outside the pipeline.

- [ ] Add "Import Job" button in `JobsView.jsx` (or Topbar) that opens a modal — Done when: button is visible in the toolbar
- [ ] Modal form: title, company, URL, status, date_applied, location, notes — Done when: form POSTs to existing `POST /api/jobs/import`
- [ ] On success: close modal, refresh job list, toast confirmation — Done when: imported job appears in the correct status tab

---

## Milestone 9: Interview Prep Module
**Goal:** When a job status changes to `interview`, auto-generate a prep sheet from the JD.

- [ ] Add `POST /api/jobs/{id}/prep` endpoint that calls LLM with JD + role — Done when: returns JSON `{likely_questions: [...], topics_to_study: [...], company_notes: "..."}`
- [ ] Add "Prep Sheet" button in `JobDrawer.jsx` visible when `status === 'interview'` — Done when: button calls the endpoint and renders the prep sheet inline below the job details
- [ ] Prep sheet LLM prompt: role-specific behavioral + technical questions, key topics, 2 sentences on the company from JD — Done when: output is coherent for an AI/ML interview

---

## Milestone 10: Email Notifications
**Goal:** Get an email when a job reaches `offer` status (or other key transitions).

- [ ] Choose delivery: Resend free tier (100 emails/day) — add `RESEND_API_KEY` to `.env.example` and `render.yaml`
- [ ] Add `_notify_offer(job)` helper in `api/main.py` using Resend SDK — Done when: POSTing to Resend sends an email to `ishani@kathuria.net`
- [ ] Call `_notify_offer` in `api_patch_job` when `new_status == 'offer'` — Done when: patching a job to offer triggers the email
- [ ] Wire Settings UI toggle "Send email notification on new offer" to `POST /api/settings` — Done when: disabling the toggle skips the send

---

## Milestone 11: Production Hardening
**Goal:** Render deployment is stable, PDFs are accessible from the deployed URL.

- [ ] Verify `render.yaml` deploys cleanly: `npm ci && npm run build` succeeds, `uvicorn` starts, `/api/stats` returns 200 — Done when: `curl https://<render-url>/api/stats` returns JSON
- [ ] Fix cross-machine PDF path resolution: `_resolve_resume_path` in `api/main.py` already handles relative/absolute but `output/resumes/` must be committed — Done when: `/api/jobs/{id}/resume` returns a PDF on Render for GHA-generated jobs
- [ ] Add startup log that prints DB backend (sqlite vs Turso) and PDF count — Done when: visible in Render logs on deploy
- [ ] Add `GET /api/health` endpoint returning `{status: "ok", db: "turso"|"sqlite", jobs: N}` — Done when: Render health check can use this instead of `/api/stats`

---

## Claude Code Commands

**Resume from any point:**
```
claude "Read PLAN.md, find the first incomplete task, and continue. Mark tasks done as you go. Commit when a milestone is complete."
```

**Work on a specific milestone:**
```
claude "Read PLAN.md and complete Milestone 7 (Settings Persistence). Mark tasks done as you go. Commit when done."
```

**Test current state:**
```
claude "Read PLAN.md. Without building anything new, test everything marked done. Start the FastAPI server and React dev server, verify /api/stats returns data, and confirm the dashboard loads. Report what works and what's broken."
```

---

## Notes & Decisions

- **LLM provider default is Groq** (`llama-3.1-8b-instant`) via Groq's free tier (console.groq.com); Gemini and Anthropic remain as fallbacks — switch via `llm.provider` in `config/settings.yaml`.
- **Turso for cloud DB** — SQLite WAL is used locally; Turso bridges to the same SQL API for GHA + Render. `seed_from_sqlite` is a no-op after first seed.
- **PDFs committed to git** — GHA commits generated PDFs so Render can serve them without a persistent disk. This works while output is <100MB; revisit if the `output/` dir grows too large.
- **No auth on the dashboard** — personal tool, Render URL is obscure enough. If shared, add HTTP Basic Auth via FastAPI middleware.
- **Workday not automated** — Workday's DOM is dynamically generated and varies per company config. A robust handler requires iframe traversal and state machine logic. For now, the browser opens and the user fills manually.
- **Settings UI currently cosmetic** — `SettingsView.jsx` renders fields with hardcoded defaults but Save does nothing. Milestone 7 fixes this.
