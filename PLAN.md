# JobApply

> Fully-automated AI/ML job pipeline (full-time new-grad + internship/co-op): scrape → score → tailor resume per JD → warm/cold email recruiters → review in React dashboard → auto-fill ATS forms → track outcomes.

---

## Viability Summary

| | |
|---|---|
| **Market** | Personal tool — no commercial intent; built for Ishani's AI/ML job search (F-1 international student, MS Applied AI @ Purdue NW, grad May 2027 / possibly Dec 2026). Now targeting **full-time new-grad AI/ML roles** first, with internships/co-ops (CPT) still in scope |
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

## Milestone 9: Interview Prep Section ☐
**Goal:** A dedicated dashboard section that turns any interview into a tailored, stored **prep pack** — generated by the LLM from the job's JD + company + Ishani's real profile, surfaced automatically when a job reaches `oa`/`interview`. (Supersedes the original thin "prep sheet button" sketch.)

> **Why (2026-07-19):** the whole pivot (M17–M19) is about landing *more* interviews; once one lands, the next bottleneck is *converting* it. Last cycle produced only 1 interview from 500+ apps — every one is precious, so prep is the highest-leverage post-interview step. Grounded in her real experience (AWS log-summarization, RAG research, multi-agent red-team), never fabricated — same discipline as the resume tailoring.
> **Fits the stack:** reuses `llm_client` + `jd_fetcher` + the profile loader; one prep row per job (regenerable); a new Sidebar section like Timeline/Outreach. Optional later: web-search company news, a mock-interview chat.

**Prep pack contents (LLM-generated, stored as JSON):**
- Company & role snapshot — what the team/product does + why she fits (2–3 sentences from JD + company).
- Topics to review — technical areas mapped from the JD (RAG eval, transformers, ML system design, the company's domain), prioritized against her background.
- Question bank in three buckets, each with talking points drawn from her real projects: **behavioral** (STAR-framed), **technical / ML-domain** (role-specific), **ML system design**.
- Questions **she** should ask the interviewer.
- Logistics/checklist — pulls `interview_date` from the job, format, a night-before list.

Tasks:
- [ ] `src/pipeline/interview_prep.py` — `generate_prep(job, jd_text, profile) -> dict` via `llm_client.complete`, strict no-fabrication system prompt (mirrors `resume_tailor`); reuses `jd_fetcher` for JD text + the shared profile text.
- [ ] `interview_prep` table in `tracker.py` (`job_id` UNIQUE, `content` JSON, `model`, `created_at`, `updated_at`) + CRUD (`upsert_prep`, `get_prep`, `delete_prep`) following the outreach/reminders table pattern.
- [ ] Endpoints: `POST /api/jobs/{id}/prep` (generate + store, returns pack), `GET /api/jobs/{id}/prep` (stored, 404 if none), `DELETE /api/jobs/{id}/prep` (clear/regen). 503/500 handling like `/tailor`.
- [ ] `apps/web/src/components/PrepView.jsx` — a **"Prep"** Sidebar section (7th nav) listing jobs at `oa`/`interview` with prep status + interview date; opens the full pack (snapshot / topics / three question buckets / questions-to-ask / checklist); "Generate" + "Regenerate" actions. Plus `App.jsx`/`Topbar`/`api.js` wiring.
- [ ] Also expose a **"Prep"** tab in `JobDrawer.jsx` when `status ∈ {oa, interview}` (reuses the same pack); the existing Dashboard focus item ("{company} interview on {date} — prep time!") deep-links to it.
- [ ] `tests/test_interview_prep.py` — `generate_prep` with a mocked LLM (asserts structure, no fabrication guard), prep-table CRUD, endpoints (generate/get/404), and the "only oa/interview jobs listed" filter.
- [ ] Gate: `flake8` clean, `pytest tests/` green, `npm run build` compiles, live-server smoke test.

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

## Milestone 13: Recruiter & Outreach Database ✅
**Goal:** SQLite schema extended with `recruiters` and `outreach` tables; full CRUD via existing tracker pattern; API endpoints wired.

> **Note:** FKs are declared but not DB-enforced (no `PRAGMA foreign_keys=ON` locally, and the Turso bridge skips PRAGMAs — enforcing in one backend but not the other would diverge). Referential integrity (cascade on recruiter delete) is enforced in `delete_recruiter()`. Blank emails store as `NULL` so multiple unknown-email recruiters coexist under the `UNIQUE` constraint.

Tasks:
- [x] `recruiters` table added in `tracker/tracker.py` `_create_tables` (id, name, email UNIQUE, company, title, linkedin_url, source, notes, created_at) — created for both sqlite + Turso backends
- [x] `outreach` table (id, recruiter_id, job_id, type, subject, body, status, sent_at, reply_received_at, follow_up_date, notes, created_at) + indexes on recruiter_id/status
- [x] CRUD in `tracker/tracker.py`: `add/get/get_by_email/list/update/delete_recruiter`, `add/get/list_outreach_for_recruiter/update_outreach/update_outreach_status`; outreach type + status constants — `tests/test_recruiter_tracker.py` → 10 passed
- [x] API endpoints in `api/main.py`: `GET/POST /api/recruiters`, `GET/PATCH/DELETE /api/recruiters/{id}`, `GET /api/recruiters/{id}/outreach`, `POST /api/outreach`, `PATCH /api/outreach/{id}` (409 on dup email, 404 on missing) — verified live: fresh `GET /api/recruiters` → `[]`, full create→list→outreach→delete cycle works; `tests/test_recruiter_api.py` → 7 passed
- [x] Gate: `flake8` clean (also cleaned pre-existing nits in `api/main.py`), `pytest tests/` → 25 passed

---

## Milestone 14: Cold Email Generator ✅
**Goal:** LLM generates a personalized cold email (or referral ask) for a given recruiter + job combination; output is a subject line + body ready to review.

> **Parsing note:** the model returns `{"subject","body"}` JSON, but pretty-prints it with literal newlines inside the body string (invalid under strict JSON). `_parse` uses `json.loads(..., strict=False)` to tolerate that, with a `Subject:`-line fallback. This was caught during the live quality check, not by mocked tests — regression test added.
> **Env note:** the local `openai` package was a stale 0.27.2 (broke Groq via `OpenAI` import — also broke local tailoring); upgraded to 2.x to run the live check. `requirements.txt` already pins `openai>=1.0.0`, so CI/Render were unaffected.

Tasks:
- [x] `pipeline/email_generator.py` — `generate_cold_email(recruiter, job, profile=None, email_type="cold") -> {subject, body}`; uses `llm_client.complete`; loads profile from `config/profile.json` if not passed; `_candidate_context` builds a factual blurb (no fabrication)
- [x] Cold email prompt: names specific role + company, 2-3 sentences of relevant background, clear 15-min/pointer ask, warm + non-generic, ≤200 words — live Groq sample reviewed: 132 words, named real projects (TrustworthyRAG) + AWS background, correct ask
- [x] Referral prompt: targets a current employee, references shared context, asks for referral/intro to hiring team, ≤150 words — live sample reviewed: reads naturally, distinct from cold copy
- [x] `POST /api/outreach/draft` ({recruiter_id, job_id?, type}) → generates + saves a `draft` outreach record → returns {id, subject, body}; maps `cold`→`cold_email`, `referral`→`referral`; 404 on missing recruiter/job — verified end-to-end against live LLM
- [x] `tests/test_email_generator.py` (8 tests, mocked LLM): parsing (JSON/fences/newlines/Subject-fallback), cold-vs-referral routing, candidate context, job=None handling
- [x] Gate: `flake8` clean, `pytest tests/` → 33 passed

---

## Milestone 15: Email Discovery & Sending
**Goal:** Given a company + name, the system guesses and optionally verifies a recruiter's email; confirmed emails can be sent from Ishani's Gmail via SMTP.

> **Reality note on SMTP probing:** RCPT verification needs outbound port 25 and a non-catch-all MX — both frequently unavailable (Google/Microsoft reject probes; most networks + Render block port 25). So `guess_emails` treats probing as best-effort: verified addresses first, else Hunter.io, else the unrejected candidate patterns ranked by likelihood. It returns `[]` only when every candidate is *explicitly* rejected and Hunter finds nothing. MX lookup uses `dnspython` (added to requirements).
> **Live send test:** `GMAIL_ADDRESS`/`GMAIL_APP_PASSWORD` aren't set in this env, so the real-send leg is deferred to first use; the send endpoint + 7-day follow-up logic were verified with `send_email` mocked (status→sent, sent_at set, follow_up = today+7), plus graceful 502 (SMTP fail, status stays draft) and 400 (recruiter has no email).

Tasks:
- [x] `pipeline/email_finder.py` — `guess_emails(first, last, domain, probe=True) -> list[str]`; 6 ranked patterns (`first.last`, `firstlast`, `flast`, `first`, `f.last`, `lastfirst`); per-candidate SMTP RCPT probe via `smtplib` (no send); MX via `dnspython` — verified: live call on `anthropic.com` returns a ranked list
- [x] `GET /api/email-finder?first=&last=&domain=&probe=` → returns the ranked JSON array — verified via handler
- [x] Hunter.io fallback in `email_finder.py`: `_hunter_lookup` calls `api.hunter.io/v2/email-finder` only when `HUNTER_API_KEY` is set, used when SMTP finds nothing; no-op without the key — covered by tests with/without key
- [x] `pipeline/email_sender.py` — `send_email(to, subject, body) -> bool` via `smtplib.SMTP_SSL` (`smtp.gmail.com:465`), creds from `GMAIL_ADDRESS`/`GMAIL_APP_PASSWORD`, returns False (logged) on any failure incl. missing creds
- [x] `POST /api/outreach/{id}/send` — sends to the recruiter's email, marks `status='sent'` + `sent_at=now`, returns `{sent, to, sent_at, follow_up_date}`; 400 if recruiter has no email, 502 on send failure (status unchanged)
- [x] `follow_up_date = sent_at + 7 days` set automatically on send — verified (sent today → follow_up 7 days out)
- [x] `tests/test_email_finder.py` (8) + `tests/test_email_sender.py` (4), both fully mocked (smtplib/MX/Hunter) — `pytest` green
- [x] Gate: `flake8` clean, `pytest tests/` → 45 passed. Env vars added to `.env.example` + `render.yaml` (also added missing `GROQ_API_KEY` to render).

---

## Milestone 16: Outreach Dashboard UI ✅
**Goal:** A new "Outreach" tab in the React dashboard lets Ishani manage recruiters, compose emails, and track replies — without leaving the app.

> **Nav note:** the app navigates via the `Sidebar` (screen state), not a top tab bar — Outreach was added as a 5th `Sidebar` nav item + `screen === 'outreach'` branch in `App.jsx` (with `Topbar` title).
> **Follow-up banner:** backed by a new `GET /api/outreach/followups` endpoint (+ `tracker.list_followups_due`) so the banner is one query, not an N+1 fetch across recruiters.
> **Local-dev fix:** added `load_dotenv()` to `api/main.py` startup — running `uvicorn` directly previously didn't load `.env`, so the draft/send endpoints failed locally without exported env vars (this surfaced during the live server smoke test). No-op in production where the platform supplies env vars.

Tasks:
- [x] `web/src/components/OutreachView.jsx` + 5th `Sidebar` nav item ("Outreach", mail icon) + `App.jsx` screen branch + `Topbar` title — `npm run build` compiles it (45 modules), live server renders the SPA
- [x] Recruiter list panel: `GET /api/recruiters` (name, title·company, email, sent count); "+ Add" inline form (name/email/company/title/notes) → `POST /api/recruiters` → refresh + auto-select — verified via live server add cycle
- [x] Per-recruiter outreach history (subject, type, sent_at, follow_up_date) with a status `<select>` (draft/sent/replied/bounced/ignored) → `PATCH /api/outreach/{id}`
- [x] Composer: "New Email" → `POST /api/outreach/draft {type:'cold'}` pre-fills subject+body; editable; "Send" persists edits via PATCH then `POST /api/outreach/{id}/send`; success toast "Email sent to {name}" — draft path verified live through the server
- [x] Referral variant: "Request Referral" button → `type:'referral'` (distinct prompt/copy)
- [x] Follow-up reminder banner: `GET /api/outreach/followups` (sent + follow_up_date ≤ today); clickable chips jump to the recruiter — `tracker.list_followups_due` unit-tested (excludes future + drafts)
- [x] "Reach out" button on `JobDrawer.jsx` → `onReachOut(job)` switches to Outreach screen, shows a job-context banner, prefills the add-recruiter company, and passes `job_id` into the draft so the LLM has the role context
- [x] Gate: `npm run build` succeeds (no errors), `pytest tests/` → 46 passed, `flake8` clean; live server smoke test green (SPA + all new endpoints)

---

## Milestone 17: Visa-Sponsorship-History Filter ✅
**Goal:** Stop spending applications on employers who won't sponsor. Score (and optionally hard-filter) each job by whether its company has a real H-1B sponsorship history, so sponsor-friendly roles rise to the top and known non-sponsors can be skipped.

> **Why (2026-07-19):** Ishani is an F-1 international student. The largest structural drag on her Summer-2026 cycle (500+ applications → 2 OAs → 1 interview) was applications hitting the "will you now or in the future require sponsorship?" auto-reject wall. Targeting known sponsors is a higher-leverage lever than raw application volume.
> **Data source:** public USCIS H-1B Employer Data Hub / MyVisaJobs top-sponsor lists — baked into a curated, refreshable JSON of normalized company names. Not a live API call, so the daily path stays offline + fast like the rest of it.
> **Soft by default:** boost-only. Unknown companies are NOT zeroed out (a small or new employer may still sponsor); a strict `require_known_sponsor` flag is available for when Ishani wants to be aggressive.

Tasks:
- [x] `config/h1b_sponsors.json` — ~130 curated known H-1B sponsors (big tech, AI labs, quant, top-volume IT-services, plus all Timeline target companies). Names normalized at load; list is refreshable.
- [x] `src/pipeline/sponsorship.py` — `is_known_sponsor(company) -> bool` (loads JSON once via `lru_cache`; normalizes lowercase + strips punctuation/suffixes; exact or **token-subset** match so "Amazon Web Services" hits "Amazon" but "Metabolic Labs" does NOT hit "Meta") and `sponsor_score(company) -> float`.
- [x] Wired into `job_filter.score_job`: the `sponsorship_friendly` (0.10) boost now fires on a known-sponsor company **OR** a JD visa keyword, so a known sponsor is boosted even when the JD says nothing about visas.
- [x] Opt-in hard filter: `filter_jobs(..., require_sponsor=False)` — when True, tags non-sponsor companies `status="skipped"` (same reversible pattern as `skip_phd`). Wired through `main.py run_pipeline` from `filters.require_known_sponsor` in `settings.yaml` (default false).
- [x] `scripts/refresh_h1b_sponsors.py` — rebuilds `h1b_sponsors.json` from the USCIS H-1B Employer Data Hub CSV (`--csv`, `--min-approvals`, `--dry-run`; unions with curated entries). Network-free; download the CSV yourself.
- [x] `tests/test_sponsorship.py` (9) — exact + suffix + token-subset matching; no substring false positive; unknown stays neutral; scoring boost; `require_sponsor=True` tags non-sponsors skipped; off by default.
- [x] Gate: `flake8` clean, `pytest tests/` → 83 passed.

---

## Milestone 18: Retarget to Full-Time New-Grad AI Roles ✅
**Goal:** Shift the pipeline's primary target from summer internships to full-time new-grad AI/ML roles (CPT co-ops still welcome), matching Ishani's timeline — the internship window has largely closed (grad May 2027; possibly Dec 2026).

> **The bug this fixed:** `job_filter.score_job` gated on `ROLE_KEYWORDS = [intern, internship, co-op, coop]` and returned 0.0 for anything else. The `newgrad-jobs.com` scraper already fetched full-time new-grad roles — but every one scored 0.0 and never got tailored. The role gate, not the scraper, was the blocker. (Verified: "Machine Learning Engineer, New Grad" scored 0.0 before, 0.675 after.)
> **Not dropping internships:** intern-list stays enabled — a Fall/Spring CPT co-op is still valuable during the school year. This is a re-prioritization (new-grad becomes first-class), not a removal.

Tasks:
- [x] `job_filter.ROLE_KEYWORDS`: added new-grad/entry-level/early-career/full-time terms (kept intern/co-op). Plus a `_role_ok()` gate that also accepts jobs from our curated feeds (`newgrad-jobs.com`/`intern-list.com` — right role type by construction) and the scraper's `season`/roleType field, so a generic-titled new-grad role isn't zeroed.
- [x] Seniority guard: `_is_too_senior()` — title-based (senior/staff/principal/lead/manager/director/architect…) plus multi-year experience requirements ("5+/7+ years"), with a JUNIOR_TITLE override so genuine new-grad roles that mention a senior-ish word survive. Applied as a soft `SENIORITY_PENALTY = 0.25` multiplier (sinks, not a hard 0).
- [x] `config/settings.yaml`: broadened `search.role_types` (new-grad/entry-level/full-time) + `deprioritize_seniority` list; noted the block is descriptive and the functional lists live in `job_filter.py`.
- [x] Confirmed `daily_tailor.yml` runs both `--source intern_list` and `--source newgrad_jobs` (both in the `all` default); the tailor step picks top-N by score across sources, so the scoring fix — not workflow ordering — is what surfaces new-grad roles. No workflow change needed.
- [x] `config/profile.json`: left as-is — `_profile_text` (resume_tailor) only reads specific fields, so a `target_roles` field would be dead config; changing the tailoring system prompt is out of scope (would alter every resume). Noted as an optional follow-up.
- [x] `tests/test_job_filter.py` (+6): new-grad / entry-level score > 0; feed-source acceptance; over-senior penalized-not-zeroed; multi-year-experience penalized; junior-title override; intern/co-op regression.
- [x] Gate: `flake8` clean, `pytest tests/` → 74 passed.

---

## Milestone 19: Recruiting Timeline & Reminders ☐
**Goal:** A dashboard **"Timeline"** view showing, per target company, its new-grad application window cross-referenced with live open roles from the scraped DB, plus reminders (apply-by + reach-out) timed to each company's window.

> **Why (2026-07-19):** For a May-2027 grad, the full-time new-grad cycle opens **Aug–Oct 2026** (now) on rolling admissions — apply-day-one matters. Ishani needs a single place that says "who's open, who's about to open, what's actually posted, and who to ping for a referral" so she doesn't miss the wave. Research: big tech opens Aug–Oct (Google's window is a tight ~2 weeks in mid-Oct), AI labs (Anthropic/OpenAI) + quant recruit rolling/earliest.
> **Referral timing (decided):** reach-out reminders fire on each company's **application window**, not her mid-2027 start date — a referral only helps while attached to a live application. This revises the earlier "defer warm outreach ~1 yr" note *for timing of the nudge* (she still chooses when to actually send).
> **"Actual dates" scope:** curated window dates per cycle (approximate — big tech is mostly rolling, so hard per-req deadlines rarely exist publicly) **+** live open-role counts from the scraped `jobs` table give ground truth on what's genuinely posted right now. Google's ~2-week window is the notable hard-close.

Tasks:
- [x] `config/recruiting_calendar.json` — 23 curated companies for the 2027 new-grad cycle: `name`, `aliases`, `opens`/`closes` (ISO dates or `rolling: true`), `program`, `sponsor`, `priority`, `tier`, `notes`, `careers_url`. Seeded from web research (big tech, AI labs, quant). Cycle-specific + refreshable.
- [x] `reminders` table in `tracker.py` (id, company, kind [`apply`|`reach_out`], due_date, done, note, created_at) + CRUD (`add_reminder`, `list_reminders`, `list_reminders_due`, `update_reminder`, `delete_reminder`) following the outreach/`list_followups_due` pattern.
- [x] `GET /api/timeline` — for each calendar company: window + computed status (`open` / `closing_soon` / `upcoming` / `closed`, or `rolling`), **live open-role count** (jobs matching an alias with an applyable status: new/queued/approved), and whether a recruiter/contact exists for it. Reads `config/recruiting_calendar.json` via `ROOT`.
- [x] Reminders endpoints: `GET /api/reminders`, `GET /api/reminders/due`, `POST /api/reminders`, `PATCH /api/reminders/{id}` (toggle done), `DELETE /api/reminders/{id}`. Match existing api/main.py Pydantic + error patterns.
- [x] `apps/web/src/components/TimelineView.jsx` — company cards grouped by status (**Open now → Upcoming → Closed**), sorted by priority → open-roles → name; sponsor + contact badges, live open-role count (click → Jobs "All" tab filtered by company via `initialSearch`), `program`/`notes`, careers link, and per-company **"Remind: apply"** / **"Remind: referral"** (toggle, default due date from the window) + **"Reach out"** (jumps to Outreach prefilled with the company).
- [x] 6th `Sidebar` nav item ("Timeline", calendar icon) + `App.jsx` `screen === 'timeline'` branch + `Topbar` title + `api.js` methods (`timeline`, `reminders`, `remindersDue`, `addReminder`, `patchReminder`, `deleteReminder`).
- [x] Reminder banner (reuses the follow-up-banner pattern) on the Timeline view: reminders due on/before today, dismissable by clicking (marks done).
- [x] `tests/test_reminders.py` (5) + `tests/test_timeline_api.py` (9) — reminders CRUD + due filter; timeline status computation (open/upcoming/closed/rolling/closing_soon) and open-role counts (incl. excluding rejected/skipped). Seed the calendar + jobs.
- [~] Gate: `flake8` clean ✅, `pytest tests/` → 68 passed ✅, live-server smoke test of `/api/timeline` + reminders CRUD ✅. `npm run build` NOT run locally (no Node on this machine) — CI `web-build` verifies compile; **`apps/web/dist` still needs a rebuild + commit on a Node machine before the Timeline tab shows on the deployed Render app.**

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
- **Strategic pivot to full-time new-grad (2026-07-19, M18)** — Ishani graduates May 2027 (possibly Dec 2026); the Summer-2026 internship cycle is over. Full-time new-grad AI/ML roles become the primary target; internships/co-ops stay in scope for CPT during the school year. The `newgrad-jobs.com` scraper already existed — the blocker was the filter's role gate zeroing every non-intern role.
- **Sponsorship-history filter is soft/boost-only (2026-07-19, M17)** — the biggest structural drag on the 500-app cycle was the "requires sponsorship?" auto-reject. Boosting known H-1B sponsors (curated USCIS/MyVisaJobs list) tilts odds better than raw volume. Unknown companies are NOT zeroed — a small/new employer may still sponsor. A strict `require_known_sponsor` flag is opt-in.
- **Outreach keeps both warm + cold; warm deferred (~1 yr)** — Ishani is on good terms with ex-AWS colleagues (some now at Google/MS/Uber) but won't reach out yet since she can't start work for ~a year. The module already supports both warm-referral and cold prompts; the timing is a manual call, not a code change. Referrals can be re-warmed a few months before availability.
