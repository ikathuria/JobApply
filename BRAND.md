# JobApply Brand Guidelines — Greenbar

> Source of truth for tokens: `apps/web/src/tokens.css` (CSS) and `apps/web/src/theme.js`
> (the same tokens as `var(--…)` for inline styles). If this doc and the tokens disagree, fix one.

## Essence
- **One line:** a personal ledger for one person's new-grad job search: triage, tailor, ATS-check, apply, track.
- **Personality:** exact, calm, legible. Never cute, never glossy, never "AI startup".
- **Reference:** 1970s tractor-feed greenbar printouts, accounting ledgers, IBM documentation.
- **Energy:** 2 of 5 · **Density:** dense tool (many rows on screen, no wasted chrome).

## Voice & copy
- Tone: direct, numeric, slightly dry. Say the number, then what to do.
- Do: "241 applications, no reply in 7+ days." · "11 points under the 90 target." · "Run ATS"
- Don't: "Unlock", "Supercharge", "Seamless", exclamation marks, emoji as icons.
- Sentence case everywhere. Mono uppercase only for column heads and status labels.

## Logo
- A square forest tile (`--accent`) with a white condensed "J", 34px in the sidebar, radius `--r-1`.
- Wordmark: "JobApply" in Plex Sans Condensed 700; tagline in mono.

## Color
| Token | Light | Dark | Use |
|---|---|---|---|
| `--bg` | #F5F7F3 | #0F1412 | page |
| `--surface` | #FFFFFF | #151C19 | drawer, inputs, panels |
| `--surface-2` | #EEF2EE | #1A2420 | subtle fills, chips |
| `--band` | #E5EFE6 | #18231D | greenbar row bands |
| `--row-hover` / `--row-sel` | #D9E8DC / #CDE3D2 | #1C2C23 / #1E3328 | list row states |
| `--ink` / `--ink-2` | #14191A / #2F3A36 | #E3EBE5 / #C2CEC6 | text |
| `--muted` | #56625D | #93A39A | secondary text |
| `--faint` | #7A8680 | #6E7D75 | non-text only (placeholder, disabled, rules) |
| `--line` | #D5DDD6 | #2A3631 | borders |
| `--accent` | #1D6B45 | #5DBB8C | primary action, selection, brand |
| `--ok` `--warn` `--bad` `--info` | #1D6B45 #8F5400 #B42318 #1F5F8B | #5DBB8C #E3A548 #F28B7D #7DB6E0 | status + data only |
| `--side-bg` | #14191A | #0A0E0C | sidebar is always dark ink |

Each signal color has a `-soft` background partner. Translucent tints use
`alpha(color, pct)` from `theme.js` (CSS `color-mix`), never hex-suffix alpha.

## Typography
| Role | Font | Size / LH | Weight |
|---|---|---|---|
| Page title | IBM Plex Sans Condensed | 34 / 1 | 700 |
| Drawer title | IBM Plex Sans Condensed | 24 / 1.15 | 700 |
| Body | IBM Plex Sans | 14 / 1.45 | 400, 600 for row titles |
| Meta | IBM Plex Sans | 12 | 400/600 |
| Numbers, IDs, column heads, statuses | IBM Plex Mono | 11–14; KPIs 26; ATS hero 64 | 500–700 |
Google Fonts with `display=swap`. All numbers are mono with `tabular-nums`.

## Layout & spacing
- 4px base: `--s-1`…`--s-8` (4, 8, 12, 16, 20, 24, 28, 40).
- Shell: dark sidebar 232px (icon rail ≤1024px, bottom tab bar ≤760px) · list · right drawer.
- Pipeline, top to bottom: ledger header with KPIs → one ruled "Today" line (top focus item ·
  follow-ups, each expands in place) → one row of stage tabs + search/filters/import → list.
  Keep chrome above the list under ~220px at 1440×900.
- Drawer sections are flat: a top rule + mono uppercase label, never boxed cards.
- Page gutter 28px desktop, 16px ≤760px. Rows 10px vertical padding.

## Shape & depth
- Radius `--r-1` (2px) on everything; `--r-2` (4px) only on floating layers.
- Shadow `--shadow-float` only on drawer/modal/popover. Rows and panels are flat.
- Ledger rules: header gets a 3px double rule in `--line-strong`; column heads a 1px ink rule.

## Signature moves
1. **Greenbar banding:** list rows band in pairs (`--band` on rows 2–3, 6–7, …), like tractor-feed paper.
2. **Ledger numbers:** match %, ATS score, KPIs and counts are IBM Plex Mono, tabular, never in pills or rings.
3. **ATS as a gauge:** the ATS score is a mono number plus a thin bar with a tick at the 90 target;
   tiers ≥90 `--ok`, 75–89 `--warn`, <75 `--bad`. Unscored jobs show a dotted-underline "run".

## Imagery & iconography
- No illustration. Icons: 16px line icons, 1.5px stroke, `currentColor`.

## Motion
- `--dur-1` 120ms for hover/background, `--dur-2` 200ms for drawer slide; `--ease`.
- ATS bar fills from 0 on first render. Respect `prefers-reduced-motion`: no fills or slides.

## Components
- **Buttons:** primary = `--accent` fill + `--on-accent`; ghost = 1px `--line` border; danger = `--bad` text. Min height 40px (36px only inside dense rows).
- **Status:** mono uppercase 11px. Ready and Offer are filled; others are text or outline in their signal color.
- **Chips (keywords):** mono 11px, `--r-1`. Matched = `--band` fill; missing = dashed `--bad` border.
- **Inputs:** `--surface`, 1px `--line`, focus ring 2px `--accent`.
- **Empty/loading:** one mono line in `--muted` ("No jobs in Ready. Tailor some from New."), no spinners bigger than 16px.

## Do / Don't
| Do | Don't |
|---|---|
| Put the number first, in mono | Score rings, gradients, glow |
| Use color for state | Rainbow pastel status pills |
| Flat rows with bands and rules | Cards inside cards, shadows on rows |
| `var(--token)` / `T.*` in components | Hex values or `${color}1A` alpha suffixes |

## Accessibility
- Text contrast (light/dark, worst case on `--row-sel`): ink 13.1/11.1, muted 4.7/5.1, accent 4.8/5.7, warn 4.5/6.2, bad 4.9/5.6. White on accent 6.5. `--faint` (≈3.5) is non-text only.
- Focus: 2px `--accent` outline, 2px offset. Targets ≥40px (44px on touch widths).
