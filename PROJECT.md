# JobApply — Project Tracker

> Living context map. Any LLM or human should be able to read this file alone and understand what the project is, how it's built, and where things are. **Keep it in sync** whenever the stack, structure, conventions, or status changes.

_Last updated: 2026-09-08_

---

## What it is

JobApply is a personal, fully-automated AI/ML job-search pipeline built for Ishani Kathuria (MS Applied AI @ Purdue Northwest, ex-AWS SDE, F-1 international student, graduating May 2027 / possibly Dec 2026). As of 2026-07-19 the primary target is **full-time new-grad AI/ML roles in the USA** (the Summer-2026 internship cycle is over); internships/co-ops stay in scope for CPT during the school year. It scrapes jobs from intern-list.com, newgrad-jobs.com, and Google Careers (US + India, browserless), scores and filters them (AI/ML relevance, role type, recency, and **H-1B sponsorship history**), tailors a resume + cover letter per job using an LLM, and lets Ishani review everything in a React dashboard. It also drafts warm-referral and cold emails to recruiters and tracks outreach. A GitHub Actions workflow runs the scrape-score-tailor pipeline daily; a Render-hosted FastAPI server serves the dashboard.

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
| Hosting | **Local-only** (run on Ishani's Mac) | — | `make local` → FastAPI serves the committed dist + API at localhost:8000, reading Turso from `.env`. Render dropped (2026-07-21). GitHub Actions + Turso stay as the free 24/7 data pipeline |
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
│  │  ├─ google_careers.py       # Google Careers — browserless (parses server-rendered ds:1 HTML blob); fans out over queries x locations (US+India) x target_levels
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
│  │  ├─ email_sender.py         # SMTP send — any mailbox (M15)
│  │  ├─ interview_prep.py       # LLM interview-prep pack generator (M9)
│  │  ├─ notifications.py        # shared status-change email (API + inbox scan)
│  │  ├─ inbox_reader.py         # read-only IMAP fetch (M20)
│  │  ├─ reply_classifier.py     # classify reply + match to a job (M20)
│  │  ├─ inbox_scan.py           # orchestrate auto status updates (M20)
│  │  ├─ ats_match.py            # JD↔profile keyword match score (M21)
│  │  ├─ followups.py            # stale-application nudges (M22)
│  │  ├─ digest.py               # weekly summary email (M23)
│  │  └─ dedup.py                # cross-source duplicate detection (M24)
│  ├─ tracker/
│  │  └─ tracker.py              # SQLite CRUD; jobs + recruiters + outreach + reminders + interview_prep tables
│  ├─ api/
│  │  ├─ main.py                 # FastAPI: all REST endpoints; serves apps/web/dist
│  │  └─ turso.py                # Turso HTTP bridge
│  └─ auto_apply/
│     ├─ apply_runner.py         # ATS detection + human-confirm loop
│     ├─ form_utils.py           # shared fill/upload/answer helpers (truthful sponsorship logic)
│     ├─ greenhouse_apply.py / linkedin_apply.py / lever_apply.py   # ✅ done
│     └─ ashby_apply.py / smartrecruiters_apply.py / workday_apply.py  # ✅ done (best-effort)
├─ apps/
│  └─ web/                       # React frontend (own package.json) — served by FastAPI
│     └─ src/
│        ├─ App.jsx              # Sidebar-driven screen routing
│        ├─ api.js               # fetch client for all /api endpoints
│        ├─ theme.js             # design tokens (warm paper/ink palette)
│        └─ components/
│           ├─ Sidebar.jsx       # nav (Dashboard/Jobs/Outreach/Timeline/Interview Prep/Analytics/Settings)
│           ├─ DashboardView.jsx / JobsView.jsx / AnalyticsView.jsx
│           ├─ TimelineView.jsx  # Recruiting calendar + open-role counts + reminders (M19)
│           ├─ PrepView.jsx      # Interview-prep packs per interview-stage job (M9)
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
| 6. Auto-Apply | ✅ done | 2026-09-05 — Ashby + SmartRecruiters + Workday handlers added; shared `form_utils.py` (fill/upload/answer + truthful full-time sponsorship answer); Greenhouse/Lever refactored onto it; runner dispatch + submit selectors wired; fake-DOM tests (29). Workday is best-effort (fills the identity step, never creates an account or auto-submits). Untested against live ATS DOMs — same caveat as the original handlers |
| 7. Settings Persistence | ✅ done | 2026-07-19 — GET/POST /api/settings (LLM provider/model, min_score, sponsor filter, source toggles) → settings.yaml + llm cache reload; SettingsView API-bound |
| 8. Import Jobs UI | ✅ done | verified 2026-07-19 — `+ Import` → ImportModal (Single Job + CSV Bulk), wired to POST /api/jobs/import |
| 9. Interview Prep Section | ✅ done | 2026-07-19 — LLM prep packs per interview (snapshot, topics, behavioral/technical/system-design Q banks, questions-to-ask, checklist); dedicated dashboard tab, stored + regenerable. JobDrawer tab deferred |
| 10. Email Notifications | ✅ done | 2026-07-19 — email on offer/interview transitions via the existing Gmail sender (not Resend); settings toggles; graceful no-op without creds |
| 11. Production Hardening | ◐ code done | 2026-07-19 — /api/health + startup logging + PDF-path resolution done; live Render deploy verification needs the user |
| 12. Scraper Pivot | ✅ done | LinkedIn/Handshake paused; intern-list + newgrad on jobright JSON API (browserless, ~1.9s/source) |
| 13. Recruiter Database | ✅ done | `recruiters` + `outreach` tables, CRUD + 8 API endpoints (25 tests) |
| 14. Cold Email Generator | ✅ done | LLM cold + referral drafts; `POST /api/outreach/draft` (33 tests) |
| 15. Email Discovery & Sending | ✅ done | email_finder (SMTP probe + Hunter), email_sender (Gmail), send endpoint + 7-day follow-up (45 tests) |
| 16. Outreach Dashboard UI | ✅ done | Outreach screen: recruiters, composer, send, follow-up banner, JobDrawer "Reach out" |
| 17. Visa-Sponsorship-History Filter | ✅ done | 2026-07-19 — boost known H-1B sponsors (~130 curated, token-subset match); opt-in require_sponsor hard filter; refresh script |
| 18. Retarget to Full-Time New-Grad | ✅ done | 2026-07-19 — broadened role gate (new-grad/entry-level/full-time + feed-source accept) + soft seniority penalty; internships/co-ops kept. New-grad roles scored 0.0 before, now surface |
| 19. Recruiting Timeline & Reminders | ✅ code done | 2026-07-19 — Timeline dashboard view: curated per-company app windows + live open-role counts + apply/reach-out reminders. Backend + tests green (68); ⚠ `apps/web/dist` needs a rebuild+commit (Node) to deploy |
| 20. Inbox Ingestion (auto status) | ✅ done | 2026-09-05 — read recruiter replies over IMAP, classify (interview/oa/rejection/offer), match to one active job, and advance status (fires notifications). Precision-biased: ambiguous mail is left alone. `--scan-inbox`; shared `pipeline/notifications.py` |
| 21. ATS Keyword Match | ✅ done | 2026-09-05 — per-job JD-vs-profile skill-keyword match % + missing-keyword chips in JobDrawer; `GET /api/jobs/{id}/ats-match` |
| 22. Application Follow-ups | ✅ done | 2026-09-05 — surfaces applied-but-stale (7d+) jobs on the Dashboard + drafts a nudge; `GET /api/applications/followups` |
| 23. Weekly Digest | ✅ done | 2026-09-05 — one SMTP summary email (new jobs, reviews, follow-ups, windows); `--digest` + opt-in weekly GHA workflow |
| 24. Cross-source Dedup | ✅ done | 2026-09-05 — group NEW listings by normalized (company,title), keep best, skip extras (reversible); `--dedup` |
| 25. Funnel Analytics | ✅ done | 2026-09-05 — response/interview rates + breakdowns by source and known-sponsor status; `GET /api/analytics/funnel` + two Analytics cards |

**In progress now:** Autonomous run (2026-09-05) — **M6 auto-apply finished** (all ATS handlers) + **six new features shipped (M20–M25):** inbox ingestion → auto status-tracking, ATS keyword match, application follow-ups, weekly digest, cross-source dedup, and funnel analytics. Email generalized to any SMTP mailbox; test suite made hermetic; `datetime.utcnow()` deprecations removed. Full tree flake8-clean; **201 pytest pass**; web build green + verified in-browser (ATS panel, funnel/sponsor cards, follow-up banner). M11's Render box is moot (Render dropped — see 2026-07-21).
**Next up (needs Ishani):** (1) put your mailbox password in `.env` as `SMTP_PASSWORD` (host/port/user already set) to enable outreach sends, notifications, **inbox scanning** (`--scan-inbox`), and the digest — all wired, all no-op safely without it; (2) run `python main.py --apply --dry-run` on a few approved jobs to sanity-check ATS auto-fill selectors, then `--apply` for real; (3) run `python main.py --dedup` to collapse the duplicate listings (e.g. the repeated "Data & AI Engineer @ Arizent"); (4) warm-referral outreach to ex-AWS/Google/MS/Uber contacts, timed to each company's window; (5) optionally add the SMTP secrets to GitHub to enable the weekly-digest workflow.

---

## Decision log

- 2026-09-05 — Shipped six conversion/hands-off features (M20–M25) — the pipeline was mature through discovery→apply→outreach→prep, so the remaining leverage was downstream of applying (last cycle: 500 apps → 1 interview). **M20 inbox ingestion** reads recruiter replies over IMAP and auto-advances job statuses — closing the loop so notifications + status tracking happen without manual entry; it's deliberately precision-biased (only acts on a clear category + exactly one matching active job + a genuine forward transition; a wrong auto-update is worse than a missed one) and read-only (never deletes/marks-read). **M21 ATS keyword match** scores a JD's skill keywords against the profile corpus and lists what's missing — targeting the auto-reject keyword filters directly; deterministic (curated vocab, no LLM), computed against `profile.json` (what she can credibly claim) since only PDFs are saved. **M22 application follow-ups** surface applied-but-stale roles (the app-side counterpart to the existing outreach follow-ups). **M23 weekly digest** is one SMTP summary so the search runs without opening the dashboard. **M24 dedup** collapses the same role arriving from multiple sources (only touches NEW jobs, reversible). **M25 funnel analytics** adds response/interview rates split by known-sponsor status — making the sponsorship thesis measurable. Shared `pipeline/notifications.py` extracted so the API and the inbox scanner emit identical milestone emails. 54 tests added (201 total). All no-op safely without SMTP/IMAP creds.
- 2026-09-05 — Finished M6 auto-apply (Ashby/SmartRecruiters/Workday) + extracted `form_utils.py` — the three "recognized but unsupported" ATSes now have handlers. Ashby and SmartRecruiters are single-page React forms (like Greenhouse/Lever), so they get full field-fill + resume upload + screening-question handlers. Workday is deliberately best-effort: it's a multi-step wizard that requires a per-employer account, and creating accounts is out of scope for an automated tool — so the handler detects a sign-in/create-account gate and stops (telling the user to log in manually and re-run), and otherwise fills only the "My Information" identity step; it never auto-advances steps or submits. All shared logic (field fill, resume upload, Yes/No answering, common screening questions) moved into `form_utils.py`, and Greenhouse/Lever were refactored onto it to kill the duplication. **Correctness fix folded in:** the old handlers answered "do you require sponsorship?" from `requires_sponsorship_internship` (False) — but after the M18 full-time pivot the truthful answer is `requires_sponsorship_fulltime` (True); answering "no" on a full-time role could get an offer rescinded. `form_utils.requires_sponsorship()` now answers YES whenever sponsorship is needed for either path (and defaults to YES when the flags are absent). Playwright imports were made lazy/optional so the whole `auto_apply` package imports without it (tests + CI don't need a browser); added 29 fake-DOM tests. Caveat unchanged from the originals: selectors are best-effort and unverified against live ATS DOMs — the human-confirm loop and `--dry-run` are the safety net.
- 2026-09-05 — Email sending generalized from Gmail-only to any SMTP mailbox — Ishani sends from a `kathuria.net` mailbox, not Gmail, so `email_sender.py` now reads `SMTP_HOST/PORT/USER/PASSWORD/FROM/SECURITY` (auto-picking SSL vs STARTTLS from the port) and falls back to the legacy `GMAIL_ADDRESS`/`GMAIL_APP_PASSWORD` when those are unset. Best-effort behavior (log + return False, never raise) is unchanged, so the send path still no-ops safely without creds. Notification recipient resolution and the send-error message were updated to match. Only manual step left for real sends: set `SMTP_PASSWORD` in `.env`.
- 2026-09-05 — Test suite made hermetic + `datetime.utcnow()` removed — `api.main` calls `load_dotenv()` at import, which injected the developer's real `.env` (SMTP_USER etc.) into `os.environ` during collection and broke `test_email_sender` (it resolved the real From address, not the mocked Gmail one). Added `tests/conftest.py` that strips credential-bearing vars once at session start, and rewrote the email-sender tests to be self-contained + cover the new SSL/STARTTLS paths. Separately, replaced every `datetime.utcnow()` (deprecated, removal-scheduled) with `datetime.now(timezone.utc)` — preserving the exact naive ISO string format where values are stored, to avoid any date-comparison drift. Result: 147 tests pass, zero project deprecation warnings, flake8-clean.
- 2026-07-21 — CI tailoring paused (`daily_tailor.yml` tailor step `if: false`) — discovery + enrich still run daily and populate Turso; resume tailoring is done on demand locally (`python main.py --tailor`) for now. Also fixed a latent bug found while pausing: the default LLM provider is `groq` (settings.yaml) and the `GROQ_API_KEY` secret exists, but the workflow only ever mapped `GOOGLE_API_KEY` into the tailor step — so CI tailoring couldn't authenticate and was failing silently (masked by `continue-on-error`). Added `GROQ_API_KEY` to the step's env so re-enabling is a single flip of `if: false` → `true`.
- 2026-07-21 — JobApply is local-only; Render deployment dropped — it's a personal single-user tool, so cloud hosting adds cost + ops (the Render build kept breaking on stale/blueprint-drifted config) for no real benefit. New model: **GitHub Actions + Turso stay** as the free, hands-off 24/7 data pipeline (daily scrape/tailor → Turso, PDFs committed to git); the **dashboard runs locally** via `make local` (FastAPI serves the committed dist + API, reading Turso from `.env`). `git pull` grabs the day's new PDFs. Zero code change — the app already reads Turso when `.env` is set and falls back to SQLite otherwise. Manual actions for Ishani: suspend/delete the Render service in its dashboard; create a local `.env` with `TURSO_DATABASE_URL` + `TURSO_AUTH_TOKEN`. `render.yaml` kept in-repo (now correct) in case cloud deploy is ever wanted again.
- 2026-07-19 — Email notifications reuse the Gmail sender, not Resend (M10) — the plan sketched Resend, but `pipeline/email_sender.py` (Gmail SMTP) already exists, is tested, and its `GMAIL_ADDRESS`/`GMAIL_APP_PASSWORD` env vars are wired. Reusing it avoids a new dependency, account, and secret. Notifications fire on `offer`/`interview` transitions (gated by settings toggles, default off), and no-op gracefully without creds. Extended past the original offer-only scope to also cover interviews, since landing interviews is the whole point of the pivot.
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
