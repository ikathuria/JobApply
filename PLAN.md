# JobApply — Roadmap: Refocus on the Apply Loop

> Forward-looking plan. Historical milestone-by-milestone build notes (M1–M25)
> now live in **PROJECT.md**'s status table + decision log — this file is the
> plan for what's next, not a record of what shipped.
>
> _Last updated: 2026-09-17_

---

## Why this plan exists

The pipeline is feature-complete through discovery → score → tailor → apply →
outreach → track → prep → analytics (M1–M25, all shipped). The problem is no
longer *missing capability* — it's that the tool is **hard to use day-to-day**.
Seven equal-weight nav items (Dashboard, Jobs, Outreach, Timeline, Interview
Prep, Analytics, Settings) and a 62 KB `JobsView` with five tabs bury the one
thing that matters daily: **review tailored jobs → approve → apply → track**.

**Goal:** make the funnel *the app*. The triage→tailor→apply loop becomes the
primary, friction-free daily surface; everything else stays but demotes to
occasional "tools." No features are removed — this is a UX re-hierarchy plus a
repo cleanup.

**Decided with Ishani (2026-09-17):**
- Core daily loop = **triage → tailor → apply**.
- Keep *all* feature areas (outreach, tracking/inbox, prep, timeline, analytics).
- Cleanup is **aggressive delete** of genuine dead weight (not features).
- Outreach is wanted — the LinkedIn connections archive drives referral/cold
  outreach via `scripts/linkedin_outreach.py`.

---

## North star: the daily loop

```
        ┌─────────── PIPELINE (primary surface) ───────────┐
  New ──▶ Ready-to-review ──▶ Approved ──▶ Applied ──▶ Interview+
  scrape   tailored PDF        you OK'd     submitted    tracked
  scored   (one-click)         it           (auto/man)   (inbox)
        └──────────────────────────────────────────────────┘
                 Tools (secondary): Outreach · Timeline · Prep · Analytics · Settings
```

One place to do the work. A contact/referral nudge and interview-prep entry
point surface *inline* on the relevant job, so you rarely leave the loop.

---

## Target UX

### Navigation — two tiers
- **Primary — "Pipeline"** (default landing): a stage-driven board that merges
  today's `Dashboard` + `Jobs`. A compact stage rail (New · Ready · Approved ·
  Applied · Interview+), main area shows the review deck for the active stage
  with big inline actions: **Tailor · Approve · Apply · Download packet ·
  set status**. "Needs action" cues (ready count, stale follow-ups) live in the
  Pipeline header.
- **Secondary — "Tools"** (under a divider, visually lighter): Outreach,
  Timeline, Interview Prep, Analytics, Settings. All kept, off the daily path.

### Component reuse, not rewrite
The focused machinery already exists inside `JobsView.jsx` — `FocusQueue`,
`ReviewDeck`, `ApprovedDeck`, `ImportModal`. This is mostly *reorganizing*
proven components behind a cleaner nav, then splitting the monolith so it stays
maintainable.

---

## Milestones

### M26 — Repo cleanup ✅ (done 2026-09-17)
- Untracked + deleted all 861 generated files under `output/resumes/`; the dir
  is now `.gitignore`d (`output/resumes/*` + `.gitkeep`). Tailoring starts fresh.
- `.gitignore` now also excludes `output/outreach/` (script reports) and `data/`
  (raw personal exports — the LinkedIn archive has private messages, phone
  numbers, logins, security challenges; **never commit it**).
- LinkedIn archive wired: only `Connections.csv` extracted → gitignored
  `data/linkedin/`. `scripts/linkedin_outreach.py` now defaults to that path,
  has a `make outreach-linkedin` target, and is verified end-to-end
  (2,373 connections → 276 shortlist, 64 at interview-stage companies).
- Still to delete (aggressive): stale one-off ops scripts
  `scripts/force_reseed_turso.py`, `scripts/pull_from_turso.py`,
  `scripts/skip_phd_jobs.py`; rotate the stale `apps/web/dist` bundles.

### M27 — Docs refresh ✅ (done 2026-09-17)
- Rewrote this PLAN.md as the refocus roadmap.
- Synced PROJECT.md: Google Careers source, `linkedin_outreach.py`, inbox
  classifier hardening, the `output/resumes` gitignore change, and the UI plan.
- Trimmed README.md: fixed stale "PDFs committed by CI" claims, corrected the
  source list, and added the LinkedIn outreach workflow.

### M28 — Two-tier navigation ✅ (done 2026-09-17)
- Rebuilt `Sidebar.jsx` into two groups: **Workspace** (Dashboard, Jobs — the
  daily loop) and a demoted **Tools** group (Outreach, Timeline, Prep,
  Analytics, Settings) under its own label / a divider when collapsed.
  Extracted a shared `NavButton`. Collapsing Dashboard + Jobs into a single
  "Pipeline" entry is deferred to M29 (needs `PipelineView`).
- Renamed the stats-section label "Pipeline" → "Funnel" to free the term.
- Fixed stale copy: user chip → "New-grad · 2026–27"; Dashboard + Analytics
  headers → "New-Grad AI/ML Job Search · 2026–27".
- Verified in-browser: both groups render, nav clicks work, build green.

### M29 — PipelineView (the core surface) ✅ (done 2026-09-17)
- New `PipelineView` composes the existing `JobsView` board (Today's Focus +
  stage tabs New→Ready→Approved→Applied→All + review/apply decks) — the stage
  rail already lives in JobsView, so this reorganizes rather than rewrites.
- Merged Dashboard + Jobs into a **single "Pipeline" primary nav entry** (default
  landing; old `dashboard`/`jobs` stored state migrates to `pipeline`).
- Folded the Dashboard's one unique "needs action" cue — stale applications due
  for follow-up — into a slim collapsible banner atop the board (deep-links to
  the Applied tab). At-a-glance funnel counts already live in the sidebar, so
  the old stat-card grid was dropped rather than duplicated.
- **Deleted `DashboardView.jsx`** (fully absorbed). Removed the now-unused
  `IconHome`; Topbar/title updated.
- Verified in-browser: default lands on Pipeline, banner expand + deep-link work,
  stage tabs switch, build green.
- Inline job entry points (**Reach out** already exists in JobDrawer; a **Prep**
  shortcut) — Reach out is wired; Prep shortcut deferred to M30/M31 polish.

### M30 — Split the JobsView monolith ✅ (done 2026-09-17)
- Extracted `ImportModal` (+ CSV helpers/constants), `FocusQueue`, `ReviewDeck`,
  and `ApprovedDeck` (+ file-download helpers) into `components/pipeline/`, with
  `TABS`/`normalizeLocation` in `pipeline/constants.js`. Trimmed now-unused
  imports from `JobsView`.
- `JobsView.jsx`: **62 KB → 18.7 KB**; every extracted file ≤15 KB (ReviewDeck
  14.7, ApprovedDeck 12.3, ImportModal 12.2, FocusQueue 3.7, constants 0.5).
- Pure refactor — the production JS bundle hash was **byte-identical** before
  and after, proving behavior is unchanged.

### M31 — Polish + verify ✅ (done 2026-09-17)
- Added an inline **Prep** shortcut to the JobDrawer (next to "Reach out"),
  shown only for OA/interview-stage jobs; it deep-links to Interview Prep and
  auto-selects that job (`PrepView` now takes an optional `focusJobId`).
- Final in-browser click-through of every view (Pipeline, Outreach, Timeline,
  Interview Prep, Analytics, Settings) — all render, nav active-state correct,
  the Prep deep-link auto-selects the job, **zero console errors, zero server
  500s**. `npm run build` green; pytest 237 green; `dist` committed.

---

## Outreach & job-search enhancements (post-roadmap, 2026-09-20/21)

The refocus roadmap (M26–M31) is complete; these build on it, driven by the
active search (warm LinkedIn referrals + F-1 sponsor prioritization).

### M32 — LinkedIn referral outreach ✅ (done 2026-09-20/21)
- `scripts/linkedin_outreach.py`: loads the LinkedIn `Connections.csv` (gitignored
  `data/linkedin/`), ranks by leverage (H-1B sponsor + live-application signal),
  and writes a worklist with a **personalized referral-ask DM per connection**.
  `--top N` focuses report/CSV/`--load`; report shows top-companies for batching.
- **In-app LinkedIn cockpit** (Outreach tab): for 1st-degree connections, an
  editable auto-generated referral DM with **Copy / Open profile / Mark as
  messaged**. "Mark as messaged" logs it via `POST /api/recruiters/{id}/log-linkedin`
  (type `linkedin`, status `sent`, +7-day follow-up) so it counts toward
  `sent_count` and enters the follow-up system. Nothing is auto-sent — DMs go
  out by hand in LinkedIn (safe + ToS-respecting).
- `lib/linkedinMessage.js` mirrors the Python template so in-app == worklist.

### M33 — Outreach & pipeline filters ✅ (done 2026-09-20/21)
- Outreach tab: **company** dropdown, **name/company/title search**, and a
  **messaged / not-messaged** filter, with an "N of M" count + Clear.
- Jobs view: **"H-1B sponsors only"** toggle in the advanced filter row.

### M34 — H-1B sponsor visibility ✅ (done 2026-09-21)
- `/api/jobs` + `/api/jobs/{id}` annotate each job with `known_sponsor` /
  `sponsor_excluded` (via `pipeline.sponsorship`). Job rows show a compact
  **H-1B** badge; the drawer header shows **H-1B SPONSOR** — sponsor-friendly
  roles are prioritizable at a glance.

### M35 — Daily reminder email ✅ (done 2026-09-21)
- `pipeline/daily_reminder.py` + `python main.py --remind`: a short daily,
  action-first email — what to **apply** to (approved/queued + top new H-1B
  sponsor roles), who to **ask for referrals** (LinkedIn connections not yet
  messaged), and **follow-ups** due. Reuses the SMTP sender; no-ops without creds.
- Scheduled via `.github/workflows/daily_reminder.yml` (daily 14:00 UTC ≈ 9 AM
  Central), opt-in on SMTP secrets. **Data caveat:** GHA reads Turso (fresh
  scraped jobs → the Apply/sponsor section is always populated); applied statuses
  + LinkedIn recruiters are local, so referral/follow-up sections only fill in
  cloud mode once that state is synced to Turso (or run `--remind` locally).

### M36 — Local→Turso sync + auto-pruning ✅ (done 2026-09-21)
- `scripts/sync_to_turso.py` (`make sync-turso`): pushes local personal state —
  tracked jobs (status != new, upsert by url), recruiters (dedup by
  linkedin_url/email/name+company), and outreach (mirrored, recruiter_id
  remapped) — up to Turso, so the cloud daily reminder's referral + follow-up
  sections populate. Never deletes Turso's scraped `new` jobs. Idempotent.
- Stale un-applied jobs (new/queued, 30d+) now pruned **daily** via a new step in
  `daily_tailor.yml`; `make tidy` prunes on demand. (Was monthly-only.)
- Once Turso creds are in `.env`, the local app reads Turso too → local + cloud
  converge on one DB (the clean end state).
- Tested with a two-SQLite stand-in for Turso (4 tests): upsert, id-remap,
  remote-`new`-preservation, idempotency.

### M37 — Inbox sync GitHub flow ✅ (done 2026-09-21)
- `.github/workflows/inbox_sync.yml` (daily 13:00 UTC, an hour before the
  reminder) runs `main.py --scan-inbox --ingest`, so jobs applied to **outside
  this tool** (LinkedIn, company sites — anything that emails a confirmation)
  are auto-tracked into Turso and show up in the daily email + follow-ups.
  Read-only on the mailbox, precision-biased. Opt-in on SMTP/Turso secrets;
  IMAP creds default to SMTP.
- Ishani's mailbox: applications in `INBOX.job apps` (default), responses in
  `INBOX.job apps.reverts` → set GitHub secret `IMAP_MAILBOX=INBOX.job apps.reverts`.
- Backlog offshoot: one-time importer for the LinkedIn `Job Applications.csv`
  export to backfill historical LinkedIn applications (the email flow covers new
  ones going forward).

### Backlog (not yet built)
- Editable **country** field on recruiters (LinkedIn export has no location, so
  a country filter needs manual data — deferred by decision 2026-09-21).
- **Email discovery** auto-fill for cold (non-connection) recruiters.
- Persisting Outreach/Pipeline filter state across navigation.

---

## Out of scope / staying as-is
- Backend pipeline (scrapers, tailoring, auto-apply, inbox, analytics) — no
  functional changes; the refocus is frontend + repo hygiene.
- Render/cloud hosting — remains dropped (local-only; GHA + Turso are the data
  pipeline). See PROJECT.md decision log (2026-07-21).
- Warm-referral *timing* — still Ishani's manual call, now informed by the
  LinkedIn shortlist + each company's window.

---

## Commands (current)

```bash
make local                      # serve committed dist + API at :8000 (daily use)
make build                      # rebuild React → apps/web/dist
make outreach-linkedin          # rank LinkedIn connections → output/outreach/
make outreach-linkedin ARGS=--load   # + upsert shortlist into recruiters table

python main.py --source newgrad_jobs   # scrape a source
python main.py --source google_careers
python main.py --tailor                # tailor top new jobs → PDFs
python main.py --scan-inbox            # read replies, auto-advance statuses
python main.py --ingest --days 60      # reconstruct funnel from the job-apps folder
python main.py --dedup                 # collapse cross-source duplicates
python main.py --digest                # weekly summary email
python main.py --remind                # daily apply/referral/follow-up nudge
python main.py --stats
```
