# Handoff: 2026-10-20 · Greenbar UI rebrand + ATS in pipeline

**Goal:** Rebrand the dashboard (apps/web) and make ATS scores visible while triaging jobs; then move on to PLAN.md work (M42–M44).
**Status:** Done, merged to `master` and pushed.

## Next step
Pick the next PLAN.md milestone (M42 portfolio polish is the quickest) → verify by `make local` and opening http://localhost:8000.

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
- UI copy still says "Approve for apply bot" / "Auto-apply queued" although auto-apply was archived (PROJECT.md decision) — candidate cleanup.
- Analytics flow chart still uses translucent fills; other secondary screens only got the token restyle, not a layout pass.

## Gotchas
- `.venv` scripts have stale shebangs (venv moved from `~/GitHub/JobApply`): `make local`/`make test` fail with `python: No such file`. Workaround: `PATH="$PWD/.venv/bin:$PATH" make test`; server: `PYTHONPATH=src .venv/bin/python -m uvicorn api.main:app --port 8000`. Real fix: recreate the venv.
- Playwright wants chromium build 1228; cached build is 1243 — pass `executable_path` to `~/Library/Caches/ms-playwright/chromium_headless_shell-1243/...`.

## Read first
- `BRAND.md`: brand rules, tokens table, layout rules
- `apps/web/src/tokens.css`: all design tokens (light + `body.dark`)
- `apps/web/src/theme.js`: token map for inline styles, `alpha()`, `atsColor`, status meta
- `PLAN.md`: open milestones M42–M44

## Uncommitted
clean
