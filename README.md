# JobApply

A personal job-search pipeline: it finds new-grad roles at H-1B-sponsoring companies,
tailors a one-page, ATS-friendly resume to each job description, scores it on demand,
and tracks every application through to offer.

**Flow:** daily discovery (GitHub Actions → Turso) → filter (sponsor history, work
authorization, start date) → tailored resume per job → optional ATS score with automatic
re-tailoring below 90 → apply → track status, replies and follow-ups.

## Run it
```bash
make install          # Python + Node deps
cp .env.example .env  # TURSO_*, SMTP/IMAP creds as needed
make local            # dashboard at http://localhost:8000
make tailor N=5       # tailor the top 5 new jobs
make test
```
Tailoring uses the [Claude CLI](https://docs.claude.com/en/docs/claude-code) (`claude -p`)
by default; Groq, Gemini or the Anthropic API can be selected in Settings.

## Layout
`main.py` CLI · `src/scrapers` discovery · `src/pipeline` filtering, tailoring, ATS
scoring, outreach, inbox parsing · `src/api` FastAPI · `apps/web` React dashboard ·
`config/` profile, settings, sponsor list · `.github/workflows` daily jobs.
See `PROJECT.md` for the full map.
