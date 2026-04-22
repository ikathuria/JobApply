# Handoff: JobApply Dashboard Redesign

## Overview
A full redesign of the JobApply Streamlit dashboard — an end-to-end AI/ML internship application system. The redesign addresses the core UX problem of **cognitive overload**: users didn't know what to do next or how to navigate the pipeline. The new design introduces a "Today's Focus" queue, a right-side job detail drawer, a clean pipeline sidebar, and a human-in-the-loop confirmation modal for auto-apply.

The current app is built with **Python + Streamlit** (`dashboard/app.py`). The goal is to **replace the Streamlit dashboard** with this redesigned UI — either as a standalone React app served alongside the Python backend, or by embedding it via `streamlit.components.v1.html()`, or by migrating the frontend to a proper React + FastAPI stack.

---

## About the Design Files
The files in this bundle are **high-fidelity HTML prototypes** created as design references — not production code to copy directly. They use React + Babel loaded from CDN and mock data. The task is to **recreate these designs** in the target environment, wiring up real data from the existing SQLite database (`tracker/applications.db`) and the existing Python pipeline.

**Fidelity: High-fidelity.** Colors, typography, spacing, interactions, and copy are all final. Recreate pixel-accurately using the codebase's patterns.

---

## Target Stack Recommendation
Since the existing codebase is Python-heavy, the recommended approach is:

1. **FastAPI** backend exposing a REST API over `tracker/applications.db`
2. **React + Vite** frontend implementing these designs
3. Run both with a single `make dev` command

Alternatively, embed the React app as a Streamlit component — but a standalone React + FastAPI setup will give a much better result.

---

## Design Tokens

### Colors
```
/* Dark theme (default) */
--bg:        #0C0C14
--surface:   #13131E
--card:      #1A1A28
--border:    #252538
--text:      #EEEEF8
--muted:     #7878A0
--accent:    #6366F1   /* primary indigo */
--accentBg:  rgba(99,102,241,0.12)
--success:   #22C55E
--warning:   #F59E0B
--danger:    #EF4444
--pink:      #EC4899

/* Light theme */
--bg:        #F4F4FA
--surface:   #FFFFFF
--card:      #FAFAFA
--border:    #E2E2EE
--text:      #1A1A2E
--muted:     #7878A0
--accent:    #4F52D9
--accentBg:  rgba(79,82,217,0.09)
--success:   #16A34A
--warning:   #D97706
--danger:    #DC2626
--pink:      #DB2777
```

### Status Colors
```
new:       #6B7280 / rgba(107,114,128,0.15)
ready:     #22C55E / rgba(34,197,94,0.15)
approved:  #8B5CF6 / rgba(139,92,246,0.15)
applied:   #3B82F6 / rgba(59,130,246,0.15)
oa:        #F59E0B / rgba(245,158,11,0.15)
interview: #EC4899 / rgba(236,72,153,0.15)
offer:     #10B981 / rgba(16,185,129,0.15)
rejected:  #EF4444 / rgba(239,68,68,0.15)
skipped:   #9CA3AF / rgba(156,163,175,0.15)
```

### Typography
```
Font stack:   "DM Sans", sans-serif
Mono stack:   "JetBrains Mono", monospace  (scores, counts, code)

Sizes:
  xs:    10px / weight 600–700
  sm:    11px / weight 500–700
  base:  12–13px / weight 400–600
  md:    15px / weight 700–800
  lg:    20px / weight 800
  xl:    24–28px / weight 800 (stat numbers, letter-spacing: -0.03em)

Section labels: 11px, weight 700, uppercase, letter-spacing 0.08em, color: muted
```

### Spacing & Radii
```
Border radius: 6px (small), 8px (inputs/buttons), 10–12px (cards), 16px (modals)
Card padding:  16px 20px
Page padding:  28px 32px
Gap (grid):    14–20px
Sidebar width: 220px
Drawer width:  440px
```

### Shadows
```
Dark: none (use border only)
Light: 0 1px 4px rgba(0,0,0,0.06)
Modal: 0 32px 80px rgba(0,0,0,0.4)
Focus ring: 0 0 0 3px <accent>18
```

---

## Screens & Views

### 1. App Shell
**Layout:** Full-viewport flex row. Left sidebar (220px, sticky) + main content (flex-1) + optional right drawer (440px, sticky).

**Sidebar** (`components/sidebar.jsx`):
- Logo block: 32×32px rounded-8 indigo square with "J", app name + subtitle
- Nav items: icon (16px) + label + optional green badge (count of ready jobs). Active state: accentBg background, accent color text, weight 700
- Spacer fills remaining height
- **Pipeline mini-stats**: colored dot + label + count in mono font for each status stage
- **Submission progress bar**: gradient indigo→green, 5px height, rounded, shows `submitted / total` with percentage
- **Theme toggle**: custom 36×20px pill switch
- **User row**: gradient avatar circle (initials), name + subtitle

**Top-level routing:** `screen` state → `"jobs"` | `"analytics"` | `"settings"`

---

### 2. Jobs Screen
**Layout:** Column flex inside main content area. Sections top→bottom:

#### 2a. Today's Focus Queue
- Section label: "TODAY'S FOCUS" (11px uppercase muted)
- Grid of 4 cards: `repeat(auto-fill, minmax(220px, 1fr))`, gap 10px
- Each card: white card with `border-left: 3px solid <itemColor>`, border-radius 10px, padding 12px 14px
- Card content: icon (16px) + description text (12px) + colored CTA link ("Label →" in item color, 11px bold)
- Hover: border-color transitions to item color, adds box-shadow `0 0 0 3px <color>18`
- Focus items (hardcoded for now, will be derived from DB):
  - Green ✦: "N jobs tailored and ready to review" → navigates to Ready tab
  - Purple ⚡: most recent ready job → opens drawer + confirm flow
  - Amber 📝: any job in OA status → opens drawer
  - Pink 🎤: any job with interview date → opens drawer

#### 2b. Tab Bar
- Tabs: New (count) | Ready (count) | Approved (count) | Applied (count) | All (count)
- Active tab: accent color, `border-bottom: 2px solid accent`, weight 700
- Count badge: accent bg + white text when active; dark bg + muted text when inactive
- "+ Import" button aligned right (secondary style, 11px)
- `border-bottom: 1px solid border` under entire tab row

#### 2c. Filter Bar
- Search input (max-width 360px, flex-1): icon "⌕", placeholder "Search title, company, location…"
- Sort select: Score ↓ | Company A–Z | Starred first
- Score range slider: 0–100%, 80px wide, shows live percentage in mono font
- Job count: right-aligned muted text

#### 2d. Job List
- Scrollable list of `JobRow` components
- Each row: `display:flex`, `align-items:center`, gap 12px, padding 10px 16px, border-radius 8px
- Active row (selected): accentBg background, `border-left: 2px solid accent`
- Hover row: slightly lighter background

**JobRow anatomy (left→right):**
1. **Score circle** (36×36px): conic-gradient ring showing score percentage in status color, white/surface inner circle (26×26px) with score number in 9px mono bold
2. **Title + company** (flex-1, truncated): 13px weight-600 title (with ★ if starred), 11px muted subtitle showing `Company · Location` (interview date in pink if present)
3. **Source tag** (hidden unless hover/active): mono 11px badge showing source name
4. **Status badge**: colored dot + label, 11px, pill shape with matching bg tint
5. **Action hint** (hover/active only): 11px bold in next-action color, e.g. "Tailor →"

**Next action mapping by status:**
```
new       → "Tailor →"   accent color
ready     → "Approve →"  #8B5CF6
approved  → "Apply →"    accent
applied   → "Track →"    #3B82F6
oa        → "Update →"   #F59E0B
interview → "Prep →"     #EC4899
offer     → "View →"     success
rejected  → "View →"     muted
skipped   → "View →"     muted
```

**Starred sorting:** Starred jobs always appear first within their sort group.

---

### 3. Job Detail Drawer
Slides in from the right (440px wide, full height sticky). Opens when a JobRow is clicked.

**Header (padding 16px 20px):**
- Job title (15px weight-800) + company/location/source tag row
- Status badge + score bar with label (inline row)
- **Primary action button**: full-width, 11px height, border-radius 9px, font weight 700
  - Color by status (see status colors)
  - new → "✦ Tailor with AI" (accent)
  - ready/approved → "⚡ Approve & Apply" (#8B5CF6) → opens Confirm Modal
  - applied → "📝 Got OA?" (#F59E0B)
  - oa → "🎤 Got Interview?" (#EC4899)
  - interview → "🎉 Got Offer?" (success)
- Close button ✕ top-right

**Tab bar:** overview | resume | cover letter (11px, uppercase, border-bottom active indicator)

**Overview tab:**
- Job description (12px, line-height 1.7, collapsed to 120px with "↓ Show more" toggle)
- Notes textarea (3 rows)
- Interview date alert card (if present): pink tint, border, "🎤 Interview: [date]"
- Date applied (if present)
- Secondary actions grid (2 cols): View Posting, Skip, Reject, Undo Tailor, Got Rejected — shown contextually by status

**Resume tab:**
- If status is `new`: empty state with "✦ Tailor Now" CTA
- Otherwise: rendered resume preview (white card, serif font, full resume content)

**Cover Letter tab:**
- If no cover letter: empty state with CTA
- Otherwise: editable textarea (18 rows, 12px, line-height 1.7) + Save/Download buttons

---

### 4. Confirm Apply Modal
Full-screen overlay (`position:fixed, inset:0`) with `backdrop-filter: blur(6px)`, `background: rgba(0,0,0,0.7)`.

**Modal card:** 560px wide, max-height 85vh, flex column, border-radius 16px, heavy box-shadow.

**Header:** Icon (36×36px, #8B5CF620 bg, ⚡) + title "Confirm Application" + subtitle "Human-in-the-loop review" + ✕ close

**Body (scrollable):**
1. Job summary card: title (15px bold), company · location · match% (green)
2. "Tailored Resume Preview" label + scrollable resume preview (max-height 240px)
3. Warning box: amber tint, ⚠️ icon, "This action cannot be undone" text
4. Checklist: 3 checkboxes — "Resume is tailored and accurate", "Cover letter looks good", "I'm ready to apply to [company]"

**Footer:**
- "Go Back" secondary button (flex: 1)
- "⚡ Submit Application" primary button (flex: 2, #8B5CF6 color)
- Submit button is **disabled** until the third checkbox (personalized "I'm ready") is checked

**Success state:** Replace modal content with celebration view — 🎉 emoji, "Application Submitted!" heading, company name, "Done" button.

---

### 5. Analytics Screen
**Layout:** Padding 28px 32px, single scrollable column, max-width unconstrained.

**Section 1 — Top stats:** 4-column grid of stat cards (total, applied, in pipeline, offers). Each: 28px bold number in status color, 11px uppercase muted label.

**Section 2 — 2-column grid:**
- Left (1.4fr): **Application Funnel** — horizontal bar chart. Each stage: label (76px fixed) + bar (height 22px, border-radius 4, shows count in white mono text inside bar) + drop-off % label. Bars fill proportionally to max value. Animate width on mount.
- Right (1fr): stacked cards:
  - **Conversion Rates**: 4 stage transitions with % label + mini progress bar
  - **Source Breakdown**: source name + count + mini bar

**Section 3 — Pipeline Flow (Sankey):** SVG `viewBox="0 0 700 160"`. Draw curved `<path>` bands connecting stages (Discovered → Applied, Applied → OA, OA → Interview, with drop-off bands going downward). Label nodes with count + stage name. Label drop-offs with counts. Use fill colors with ~30% opacity for bands.

---

### 6. Settings Screen
**Layout:** Padding 28px 32px, max-width 640px, scrollable.

**Sections** (11px uppercase section headers):
1. **Your Profile** — 2-col grid: Full Name, Email, LinkedIn URL, GitHub URL, Location, Target Role
2. **API Keys** — warning banner + Gemini API Key + Anthropic API Key (password type inputs)
3. **Discovery Preferences** — source checkboxes + Min Score Threshold + Max Daily Applications
4. **Application Behavior** — 4 checkboxes (Require approval, Auto-screenshot, Email on offer, Auto-skip)
5. Save / Reset buttons

---

## Interactions & Behavior

### Navigation
- Clicking sidebar nav item changes `screen` state
- Clicking a tab changes `tab` state (also resets job selection)
- Clicking Today's Focus card either changes tab or opens job drawer (if jobId present)
- `screen` + `tab` + `dark` persisted to `localStorage` as `"ja_state"` JSON

### Job Selection / Drawer
- Click any JobRow → `setSelectedJob(job)` → drawer slides in from right
- Drawer does not navigate away — list remains visible and scrollable
- Clicking ✕ or submitting application → `setSelectedJob(null)` closes drawer

### Confirm Apply Flow
1. Click "⚡ Approve & Apply" in drawer header
2. Confirm modal opens (state: `"review"`)
3. User scrolls through resume preview, checks 3 checkboxes
4. Submit button activates only when third checkbox is checked
5. On click → state transitions to `"done"` (success screen)
6. "Done" button → closes modal + closes drawer + status update

### Theme Toggle
- Sidebar pill switch toggles `dark` boolean
- All colors reference theme tokens derived from `dark ? DARK : LIGHT`
- Transition: `background-color 0.18s ease, border-color 0.18s ease, color 0.18s ease`

### Animations
- Job row hover: instant bg change
- Score circle: no animation needed (static)
- Funnel bars: `transition: width 0.6s ease` on mount
- Modal: appears instantly (no animation required, blur overlay provides context)
- Focus queue card hover: `border-color` + `box-shadow` transition 0.15s

---

## API Endpoints Needed
Implement these FastAPI endpoints reading from `tracker/applications.db`:

```
GET  /api/stats                    → { total, new, ready, applied, oa, interview, offer, rejected, skipped }
GET  /api/jobs?status=&search=&min_score=&sort=&page=&limit=
GET  /api/jobs/:id
PATCH /api/jobs/:id                → { status?, notes?, starred?, date_applied?, ... }
POST /api/jobs/:id/tailor          → triggers pipeline/resume_tailor.py + cover_letter.py
POST /api/jobs/:id/apply           → triggers auto_apply runner (dry_run param)
GET  /api/jobs/:id/resume          → returns PDF binary
GET  /api/jobs/:id/cover_letter    → returns text
PATCH /api/jobs/:id/cover_letter   → { text }
GET  /api/focus                    → returns top 4 focus items derived from DB state
```

---

## State Shape (React)
```typescript
interface AppState {
  dark: boolean;
  screen: "jobs" | "analytics" | "settings";
  tab: "new" | "ready" | "approved" | "applied" | "all";
  selectedJob: Job | null;
  confirmJob: Job | null;
}

interface Job {
  id: number;
  title: string;
  company: string;
  location: string;
  score: number;           // 0.0–1.0
  status: JobStatus;
  source: "intern_list" | "linkedin" | "handshake";
  url: string;
  description?: string;
  starred: boolean;
  dateApplied?: string;    // ISO date
  notes?: string;
  coverLetter?: string;
  resumePath?: string;
  interviewDate?: string;
  rejectionStage?: string;
}

type JobStatus = "new" | "ready" | "approved" | "applied" | "oa" | "interview" | "offer" | "rejected" | "skipped";
```

---

## Files in This Bundle
```
design_handoff_jobapply_redesign/
├── README.md                    ← this file
├── JobApply Redesign.html       ← main prototype (open in browser)
└── components/
    ├── data.js                  ← mock data + status metadata
    ├── ui-kit.jsx               ← ThemeCtx, base components (Btn, Card, Input, etc.)
    ├── sidebar.jsx              ← Sidebar nav component
    ├── jobs-view.jsx            ← FocusQueue, JobRow, JobsView
    ├── job-drawer.jsx           ← JobDrawer + ConfirmModal
    ├── analytics-settings.jsx   ← AnalyticsView + SettingsView
    └── app.jsx                  ← Root App, routing, Tweaks panel
```

**To run the prototype:** Open `JobApply Redesign.html` in any modern browser. No build step needed. Click any job row to open the detail drawer. Use the Tweaks panel (toolbar button) to switch themes and navigate screens.

---

## Notes for Claude Code
- The existing `dashboard/app.py` Streamlit code is the source of truth for all data logic, status transitions, and pipeline triggers — preserve all that behavior.
- The SQLite schema is in `tracker/tracker.py` — read it carefully before writing API endpoints.
- The `IS_CLOUD` flag in the existing code controls whether local browser commands (Playwright) are available — carry this forward.
- Keyboard shortcuts (`j`/`k` to navigate, `a` to act, `s` to skip) mentioned in the existing app should be implemented — they're not in the prototype but the user values them.
- The "Tailor" action is slow (LLM call) — show a loading state in the drawer while it runs.
- All PDF paths in the DB may be absolute Windows paths — normalize to relative when serving from FastAPI.
