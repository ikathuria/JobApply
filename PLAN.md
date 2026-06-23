# JobApply

> Fully-automated AI internship pipeline: scrape → score → tailor resume per JD → cold email recruiters → review in React dashboard → auto-fill ATS forms → track outcomes.

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

# Required for cold email sending (Gmail SMTP)
GMAIL_ADDRESS=          # e.g. defeated.social@gmail.com
GMAIL_APP_PASSWORD=     # Google Account → Security → App Passwords → generate one

# Optional — Hunter.io email finder (25 free searches/month)
HUNTER_API_KEY=         # hunter.io → dashboard → API key
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

---

## Milestone 12: Scraper Pivot ✅
**Goal:** intern-list.com + newgrad-jobs.com run daily; LinkedIn and Handshake are paused cleanly (not deleted).

> **Reality note:** intern-list.com and newgrad-jobs.com embed a *virtualized
> jobright.ai table* (not static HTML). The table is backed by a public JSON
> endpoint — `POST jobright.ai/swan/mini-sites/list?position=N&count=50` with body
> `{"category": "<type>:us:ml_ai"}` — which serves anonymously. So the scrapers use
> plain `requests` (no Playwright, no bs4). Shared paging/normalization lives in
> `scrapers/jobright_minisite.py`; the two site modules just pin a category slug
> (`newgrad:us:ml_ai`, `intern:us:ml_ai`). This made the whole daily discovery path
> browserless, so CI no longer installs Chromium.

Tasks:
- [x] Pause "Discover - LinkedIn" and "Discover - Handshake" in GHA via `if: false` (steps retained for re-enable) — also set `enabled: false` in `config/settings.yaml`
- [x] Update the `sources` input description to `all / intern_list / newgrad_jobs`
- [x] Reverse-engineer the jobright JSON API; build `requests`-based paging/normalization in `scrapers/jobright_minisite.py`; refactor `intern_list_scraper.py` + create `newgrad_jobs_scraper.py` as thin category-slug wrappers — verified: live pull of 150 jobs each in ~1.9s, deduped, well-formed
- [x] Add `newgrad_jobs` to `--source` choices in `main.py` + discovery branch wired to `scrape_newgrad_jobs`; `newgrad_jobs` source added to `settings.yaml` (enabled)
- [x] Add "Discover - newgrad-jobs.com" GHA step (runs on `sources == 'all'` or `'newgrad_jobs'`, `continue-on-error: true`); drop the Chromium install step (daily path is now browserless)
- [x] `tests/test_newgrad_scraper.py` (wrapper contract) + `tests/test_jobright_minisite.py` (pagination/normalization/dedupe via mocked `requests.post`); `pytest tests/` → 8 passed
- [x] Gate: `flake8` clean on touched files (repo `setup.cfg` added), `pytest` green

---

## Milestone 13: Recruiter & Outreach Database
**Goal:** SQLite schema extended with `recruiters` and `outreach` tables; full CRUD via existing tracker pattern; API endpoints wired.

Tasks:
- [ ] Add `recruiters` table migration in `tracker/tracker.py` (alongside existing jobs table): columns `id INTEGER PK`, `name TEXT`, `email TEXT UNIQUE`, `company TEXT`, `title TEXT`, `linkedin_url TEXT`, `source TEXT` (manual/hunter/guessed), `notes TEXT`, `created_at TEXT` — Done when: `python -c "from tracker.tracker import Tracker; t=Tracker(); t.create_tables()"` creates the table without error on a fresh DB
- [ ] Add `outreach` table: `id INTEGER PK`, `recruiter_id INTEGER FK→recruiters`, `job_id INTEGER FK→jobs (nullable)`, `type TEXT` (cold_email/referral), `subject TEXT`, `body TEXT`, `status TEXT` (draft/sent/replied/bounced/ignored), `sent_at TEXT`, `reply_received_at TEXT`, `follow_up_date TEXT`, `notes TEXT` — Done when: table created, FK constraint tested
- [ ] Add CRUD methods to `tracker/tracker.py`: `add_recruiter`, `get_recruiter`, `list_recruiters`, `update_recruiter`, `delete_recruiter`, `add_outreach`, `get_outreach`, `list_outreach_for_recruiter`, `update_outreach_status` — Done when: `pytest tests/test_recruiter_tracker.py` passes (write tests in same task)
- [ ] Add API endpoints in `api/main.py`: `GET /api/recruiters`, `POST /api/recruiters`, `GET /api/recruiters/{id}`, `PATCH /api/recruiters/{id}`, `DELETE /api/recruiters/{id}`, `GET /api/recruiters/{id}/outreach`, `POST /api/outreach`, `PATCH /api/outreach/{id}` — Done when: `curl -s http://localhost:8000/api/recruiters` returns `[]` on a fresh DB
- [ ] Gate: lint and tests pass — Done when: all green

---

## Milestone 14: Cold Email Generator
**Goal:** LLM generates a personalized cold email (or referral ask) for a given recruiter + job combination; output is a subject line + body ready to review.

Tasks:
- [ ] Create `pipeline/email_generator.py` with function `generate_cold_email(recruiter: dict, job: dict, profile: dict, email_type: str) -> dict` where `email_type` is `cold` or `referral`; uses existing `llm_client.py` (Groq default); returns `{subject: str, body: str}` — Done when: unit test with mocked LLM returns expected keys
- [ ] Cold email prompt: opening that names the specific role + company, 2–3 sentences on Ishani's relevant background (MS AI @ Purdue, ex-AWS, RAG/LLM focus), a clear ask ("Would you have 15 minutes to connect, or could you point me to the right contact?"), sign-off. Tone: warm, direct, not generic. Max 200 words. — Done when: manual review of 3 sample outputs is coherent and non-generic
- [ ] Referral ask prompt: targets a current employee (not recruiter); references mutual context if available (alumni, shared interest); asks specifically for a referral or intro to the hiring team. Max 150 words. — Done when: manual review of 2 sample outputs reads naturally
- [ ] Add `POST /api/outreach/draft` endpoint: accepts `{recruiter_id, job_id (optional), type}`, calls `generate_cold_email`, saves result as a `draft` outreach record, returns `{id, subject, body}` — Done when: `curl -X POST http://localhost:8000/api/outreach/draft -d '{"recruiter_id":1,"type":"cold"}'` returns a subject + body
- [ ] Add `pytest` unit tests for `email_generator.py` with mocked `llm_client` — Done when: `pytest tests/test_email_generator.py` passes
- [ ] Gate: lint and tests pass — Done when: all green

---

## Milestone 15: Email Discovery & Sending
**Goal:** Given a company + name, the system guesses and optionally verifies a recruiter's email; confirmed emails can be sent from Ishani's Gmail via SMTP.

Tasks:
- [ ] Create `pipeline/email_finder.py` with `guess_emails(first: str, last: str, domain: str) -> list[str]`; generates the 6 most common patterns (`first@`, `firstlast@`, `first.last@`, `flast@`, `f.last@`, `lastfirst@`); verifies each via SMTP RCPT probe (no-send check, `smtplib`); returns list sorted by likelihood — Done when: `python -c "from pipeline.email_finder import guess_emails; print(guess_emails('john','smith','anthropic.com'))"` returns a list (may be empty if all bounce)
- [ ] Add `GET /api/email-finder?first=X&last=X&domain=X` endpoint that calls `guess_emails` and returns the ranked list — Done when: curl returns a JSON array
- [ ] Optional Hunter.io integration in `email_finder.py`: if `HUNTER_API_KEY` is set, call `https://api.hunter.io/v2/email-finder` as a fallback when SMTP probing finds nothing; skip gracefully if key is not set — Done when: the function works with and without `HUNTER_API_KEY` in env
- [ ] Create `pipeline/email_sender.py` with `send_email(to: str, subject: str, body: str) -> bool`; uses `smtplib.SMTP_SSL` with Gmail (`smtp.gmail.com:465`); credentials from `GMAIL_ADDRESS` + `GMAIL_APP_PASSWORD` env vars; returns `True` on success, logs error and returns `False` on failure — Done when: unit test with mocked SMTP passes; live test (guarded by `GMAIL_ADDRESS` in env) sends a real email to `defeated.social@gmail.com`
- [ ] Add `POST /api/outreach/{id}/send` endpoint: loads the draft outreach record, calls `send_email`, sets `status='sent'` + `sent_at=now`, returns `{sent: true}` — Done when: curl sends a real email and the DB record is updated
- [ ] Set `follow_up_date = sent_at + 7 days` automatically on send — Done when: outreach record has `follow_up_date` set after send
- [ ] Add `pytest` tests for `email_sender.py` (mocked SMTP) and `email_finder.py` (mocked `smtplib`) — Done when: `pytest tests/test_email_sender.py tests/test_email_finder.py` passes
- [ ] Gate: lint and tests pass — Done when: all green

---

## Milestone 16: Outreach Dashboard UI
**Goal:** A new "Outreach" tab in the React dashboard lets Ishani manage recruiters, compose emails, and track replies — without leaving the app.

Tasks:
- [ ] Create `web/src/OutreachView.jsx`; add it to the tab bar in `web/src/App.jsx` as the 5th tab ("Outreach") — Done when: clicking the tab renders the component without a console error
- [ ] Recruiter list panel: fetches `GET /api/recruiters`, displays name + company + email + # emails sent; "Add Recruiter" button opens an inline form (name, email, company, title, notes); on submit POSTs to `POST /api/recruiters` and refreshes list — Done when: adding a recruiter appears in the list immediately
- [ ] Per-recruiter outreach panel: clicking a recruiter shows their outreach history (subject, status, sent_at, follow_up_date); each row has a status dropdown (sent/replied/bounced/ignored) that PATCHes `PATCH /api/outreach/{id}` on change — Done when: status changes persist on reload
- [ ] Email composer: "New Email" button on a recruiter row; calls `POST /api/outreach/draft` with `{recruiter_id, type: 'cold'}` to pre-fill subject + body; user edits in a textarea; "Send" button calls `POST /api/outreach/{id}/send`; success shows a toast "Email sent to {name}" — Done when: full flow (draft → edit → send) completes without page reload
- [ ] Referral variant: "Request Referral" button (same flow but `type: 'referral'`); appears alongside "New Email" — Done when: referral draft generates different copy from cold email draft
- [ ] Follow-up reminder banner: if any outreach has `status='sent'` and `follow_up_date <= today`, show a yellow banner at the top of OutreachView listing those recruiters — Done when: banner appears when a test record with `follow_up_date = yesterday` exists
- [ ] "Reach Out" button on `JobDrawer.jsx`: opens the email composer pre-linked to the job (`job_id` passed to draft endpoint); if no recruiter is selected for this job, prompts user to pick or add one first — Done when: clicking the button from a job opens the composer with the job title/company pre-filled in the LLM prompt context
- [ ] Gate: `npm --prefix web run build` succeeds with no type errors; manual click-through of the full Outreach tab flow — Done when: all green and no console errors

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
- **LinkedIn and Handshake PAUSED (2026-06-22)** — both scrapers disabled in GHA via `if: false`; code and secrets retained for easy re-enable. Replaced by newgrad-jobs.com (Milestone 12).
- **Cold email via Gmail SMTP** — using app password + `smtplib.SMTP_SSL` avoids the OAuth2 dance. Gmail allows 500 sends/day, well within personal outreach volume. App password requires 2FA on the account.
- **Email discovery: SMTP probing first, Hunter.io optional** — SMTP RCPT probing is free and works ~50–60% of the time for common domains. Hunter.io (25 free/month) is reserved for high-priority targets. Manual entry is the primary UI path for precise control.
- **Referral vs cold email are separate LLM prompts** — cold targets recruiters/HR; referral targets engineers/PMs at the company. Different tone, different ask, same send infrastructure.
- **No auto-send** — all emails go through a draft-review-send flow in the UI. The system never sends without user confirmation.
