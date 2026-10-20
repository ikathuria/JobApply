# JobApply — Project Context

> Read this first; it is the whole map. Full history (M1–M44 decision log) lives in
> `archive/docs/PROJECT-history.md` — only open it if a decision below isn't enough.

_Last updated: 2026-10-20_

## What it is
Personal job-search tool for Ishani Kathuria (MS Applied AI @ Purdue Northwest, May
2027; ex-AWS SDE; F-1 → OPT from May 2027, no CPT, needs H-1B sponsorship later).
Targets **full-time new-grad roles in the US**, priority **AI/ML → SWE → Data Science
→ ML Research**. Runs locally on her Mac; GitHub Actions + Turso keep data fresh.

## The flow
1. **Discover** (GHA daily, `daily_discover.yml`): intern-list + newgrad-jobs (jobright
   JSON API; newgrad verticals `ml_ai, swe, data_science, data_analysis`) → `job_filter`
   → Turso. Skipped on insert: non-H-1B-sponsors (`filters.require_known_sponsor`),
   work-auth blockers (clearance, citizenship/ITAR, "no sponsorship"), roles starting
   before May 2027 (`timing_blocker`), PhD-only. Then enrich new jobs' full JD, prune 30d+.
2. **Tailor** (local, `make tailor N=5` or the drawer's *Tailor* button) —
   `pipeline/tailor_flow.py`: enrich → JD → re-check work-auth + start date → title →
   resume **track** (`resume_tracks.py`) → `resume_tailor` via **Claude CLI, Haiku** →
   `output/resumes/<id>_<slug>/{resume.pdf, tailored.json, jd.txt}` → status `queued`.
3. **Review** (dashboard): optional **ATS score** button → `ats_score.py` with **Sonnet**;
   below 90 it re-tailors (Haiku) with the feedback, max 2 rounds, keeps the best, never
   adds keywords the profile can't support (`unsupported` = real gaps). Cover letter only
   on demand.
4. **Apply by hand**, then set status in the dashboard (applied → oa/interview/offer/rejected).
   `inbox_sync.yml` also ingests confirmation/reply emails; reminders + digest email daily/weekly.

## Stack
Python 3.12 (CI) / 3.14 (local venv) · FastAPI + React 18/Vite (built `apps/web/dist`
committed, served by FastAPI) · SQLite locally / Turso (libsql HTTP) when `TURSO_*` in
`.env` · ReportLab PDFs · LLM via `pipeline/llm_client.py`: provider `claude_cli`
(`claude -p`, subscription-billed, account = `llm.claude_cli_config_dir`), Groq/Gemini/
Anthropic API selectable in Settings.

## Structure
```
main.py                CLI: discover (default) | --tailor | --base-resumes | --recruiters | --stats | --scan-inbox | --digest | --remind | --dedup
config/
  profile.json         resume source of truth: experience, 13 projects, skills, tracks (4 resume variants)
  settings.yaml        sources, filters, llm (claude_cli_model: haiku, ats_model: sonnet)
  h1b_sponsors.json    known sponsors (scripts/refresh_h1b_sponsors.py)
src/
  scrapers/            jobright_minisite (shared), newgrad_jobs, intern_list, google_careers, linkedin_* (recruiters)
  pipeline/
    job_filter.py      scoring + skip rules (EXCLUDE_PATTERNS, TIMING_PATTERNS, PhD, sponsor)
    tailor_flow.py     the one tailoring flow (CLI + API) + ATS + cover letter on demand
    resume_tracks.py   title → track; per-track profile view; base resumes
    resume_tailor.py   tailoring prompt (track-narrowed profile, optional ATS feedback)
    ats_score.py       LLM ATS scorer + re-tailor loop     ats_match.py  deterministic keyword match
    llm_client.py      provider switch; claude_cli strips ANTHROPIC_API_KEY, logs tokens
    pdf_generator.py   resume / cover-letter PDFs
    jobright_enricher.py, jd_fetcher.py, sponsorship.py, dedup.py
    outreach: email_generator, email_finder, email_sender · inbox: inbox_reader, inbox_scan,
    reply_classifier, application_parser · notices: notifications, daily_reminder, digest,
    followups · interview_prep.py
  api/main.py          REST API (+ turso.py adapter)
  tracker/tracker.py   schema + migrations (ALTER TABLE list), status constants
apps/web/src/          React dashboard (JobDrawer.jsx = tailor / ATS / cover letter / status)
scripts/               enrich_jobs, cleanup_stale_jobs, linkedin_outreach, refresh_h1b_sponsors
.github/workflows/     ci, daily_discover, inbox_sync, daily_reminder, weekly_digest
archive/               retired code + old docs — do not read unless asked
```

## Commands
```
make local            # dashboard at http://localhost:8000
make tailor N=5       # tailor top 5 new jobs (Haiku)
make base-resumes     # 4 one-page track PDFs → output/resumes/base/
make discover         # scrape now (GHA does it daily)
make test             # pytest (pythonpath=src via pyproject)
make build            # after editing apps/web/src
```

## Conventions
- Never fabricate resume content: tailoring and ATS rewrites use only `profile.json`;
  add a skill there only when Ishani confirms she can defend it in an interview.
- Usage budget matters: Haiku for bulk, Sonnet only on explicit button press; no cover
  letters by default; each CLI call is isolated (no tools, empty cwd, ~1k-token overhead).
- Schema changes: add to the `ALTER TABLE` list in `tracker._create_tables` (works for Turso too).
- Commits: no AI attribution trailers (portfolio repo). Rebuild `apps/web/dist` and commit it
  when the frontend changes.

## Key decisions (one line each; details in the history doc)
- Local-only app; GHA + Turso are the 24/7 data pipeline (Render dropped 2026-07-21).
- Claude CLI over APIs (2026-10-19): Sonnet-quality tailoring billed to the subscription.
- Filters skip, not just down-score (2026-10-20): score 0 alone still landed in "new".
- Applying is manual (auto-apply archived 2026-10-20); the tool tailors, scores, tracks.
- Four resume tracks chosen by job title (2026-10-19); DeepfakeGuard kept off the resume
  until its detector is real.
- Tailored resumes are forced to one page: prompt limits + `fit_one_page` caps + render-and-
  trim (`shrink_to_one_page` with `pdf_generator.resume_page_count`).
- Dashboard UI follows `BRAND.md` (Greenbar, 2026-10-20): tokens in `apps/web/src/tokens.css`;
  ATS score shown in list rows + drawer; `sort=ats` on `/api/jobs`.
- Jobright bot-checks fast crawls (2026-10-20): its "Security check" page raises
  `JobrightBlocked` — never treat it as "closed" (that once skipped 158 live jobs).
  Enrichment runs at 8 s/request with back-off and stops after 3 blocks; JD fetch never
  scrapes jobright HTML. Setting `JOBRIGHT_EMAIL/PASSWORD` in `.env` may help locally.

## Status / next
Greenbar rebrand merged 2026-10-20. See `HANDOFF.md`, then `PLAN.md`.
