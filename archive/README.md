# Archive

Retired code and superseded docs, kept for history. Nothing here is imported, run,
or tested. AI coding sessions are told not to read this folder (see `CLAUDE.md`).

| Path | What | Retired |
|---|---|---|
| `auto_apply/`, `tests/test_auto_apply.py`, `tests/test_form_utils.py` | Playwright ATS form-filling (Greenhouse, Lever, Workday, …) | 2026-10-20 — applying is manual; the tool tailors + tracks |
| `scrapers/handshake_scraper.py` | Handshake scraper (Playwright) | paused 2026-06-22, archived 2026-10-20 |
| `workflows/monthly_cleanup.yml` | Monthly prune | superseded by the daily prune in `daily_discover.yml` |
| `scripts/sync_to_turso.py`, `tests/test_sync_to_turso.py` | Local SQLite → Turso push | local app reads Turso directly (single DB) |
| `tests/test_api.py` | Manual API smoke script | covered by the pytest API tests |
| `render.yaml` | Render deploy blueprint | Render dropped 2026-07-21 (local-only) |
| `output-google/` | One-off Google outreach notes | — |
| `docs/PROJECT-history.md` | Full project tracker incl. the M1–M44 decision log | slimmed 2026-10-20 |
| `docs/PLAN-history.md` | All milestone plans M1–M44 | slimmed 2026-10-20 |
| `docs/README-full.md` | Long-form README | slimmed 2026-10-20 |

To restore something: `git mv archive/<path> <original path>` and re-add any
CLI flag / workflow step it needed (see the history doc for how it was wired).
