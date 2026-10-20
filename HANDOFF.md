# Handoff: 2026-10-20 · Greenbar UI rebrand + ATS in pipeline

**Goal:** Rebrand the dashboard (apps/web) and make ATS scores visible while triaging jobs; then move on to PLAN.md work (M42–M44).
**Status:** Done, merged to `master` and pushed.

## Next step
Do these first, in order, then move on to PLAN.md (M42 portfolio polish is the quickest):
1. **Recreate `.venv`.** It was moved from `~/GitHub/JobApply`, so its scripts point at a dead interpreter path.
   Run `rm -rf .venv && python3.14 -m venv .venv && .venv/bin/pip install -r requirements.txt && .venv/bin/pip install -e .`
   → verify `.venv/bin/uvicorn --version` and `.venv/bin/pytest -q` both run.
2. **Make `make` independent of the shell PATH.** In `Makefile`, add `PY := .venv/bin/python` and replace the bare
   `python`/`pip`/`uvicorn` calls with `$(PY)`, `$(PY) -m pip` and `$(PY) -m uvicorn`. The local/dev/api targets
   also need `PYTHONPATH=src` or `--app-dir src` if `pip install -e .` doesn't cover `api.main`.
   → verify `make test` (250 pass) and `make local` serves http://localhost:8000.
3. **Remove the auto-apply leftovers from the UI.** Auto-apply was archived (PROJECT.md), but `apps/web/src/components/JobDrawer.jsx` still says:
   L11 "Approved for the apply bot", L387 "Approve for apply bot", L691–693 "Auto-apply queued … apply bot will pick
   this up", and L131 mentions "outside the ap…". Reword them for manual applying, e.g. "Approve to apply" and
   "Approved: open the posting and apply, then mark applied". Also grep `src/` for any leftover auto-apply text
   (the `/api/focus` labels). → verify with `make build`, check `grep -rni "apply bot\|auto-apply" apps/web/src src` is clean, then commit.

## Done this session
- Greenbar brand: `BRAND.md` + `apps/web/src/tokens.css` (single source of truth); `theme.js` maps to CSS vars (e2af6a1)
- All components de-hexed (no hard-coded colors, radius 2px, IBM Plex fonts, no emoji icons)
- ATS: score + 90-target gauge column in list rows (`JobRow.jsx`, `AtsScore` in `ui/index.jsx`); `sort=ats` in `src/api/main.py`; Sonnet ATS report at top of drawer Overview (`AtsScorePanel` in `JobDrawer.jsx`)
- Layout: one-line Today strip (`PipelineView.jsx`), tabs + search on one row (`JobsView.jsx`), flat drawer sections, bottom tab bar ≤760px; `FocusQueue.jsx` deleted
- Verified: `make test` 250 passed; axe critical/serious clean on all screens light+dark; no page h-scroll 320–2560

## Decisions
- Greenbar (ledger/greenbar printout, forest #1D6B45, IBM Plex): user's pick from 4 previews. Rejected: Docket, Departures, Riso Zine.
- Light-first; default theme only changes for users with no saved setting (user's saved setting is dark).
- Daily-tool density over portfolio polish (user: "just me, daily tool").

## Open threads
- Only job #19024 has an ATS score (79); all other rows show "run" until scored (each run = one Sonnet call).
- Analytics flow chart still uses translucent fills; other secondary screens only got the token restyle, not a layout pass.

## Gotchas
- `.venv` scripts have stale shebangs (venv moved from `~/GitHub/JobApply`): `make local`/`make test` fail with `python: No such file`. Workaround until Next step 1–2 is done: `PATH="$PWD/.venv/bin:$PATH" make test`; server: `PYTHONPATH=src .venv/bin/python -m uvicorn api.main:app --port 8000`.
- Playwright wants chromium build 1228; cached build is 1243 — pass `executable_path` to `~/Library/Caches/ms-playwright/chromium_headless_shell-1243/...`.

## Read first
- `BRAND.md`: brand rules, tokens table, layout rules
- `apps/web/src/tokens.css`: all design tokens (light + `body.dark`)
- `apps/web/src/theme.js`: token map for inline styles, `alpha()`, `atsColor`, status meta
- `PLAN.md`: open milestones M42–M44

## Uncommitted
clean
