#!/usr/bin/env python3
"""
Turn a LinkedIn `Connections.csv` export into a ranked outreach worklist.

Ishani has hundreds of 1st-degree connections. This script filters them down
to people worth reaching out to for the new-grad AI/ML search — recruiters on
relevant teams and engineers who could refer — at companies that actually
matter (known H-1B sponsors + companies where she already has a live
application), then ranks them by leverage.

Company relevance reuses `pipeline.sponsorship.is_known_sponsor` (the same
curated H-1B list the scorer uses) so we don't maintain a second company list.
Companies where she has an applied/interviewing/starred job are pulled from the
tracker DB and treated as the top tier — a warm contact where an application is
already in flight is the highest-value outreach.

Usage:
    # Preview the ranked list (writes a markdown report + CSV, no DB writes).
    # Defaults to the gitignored data/linkedin/Connections.csv:
    python scripts/linkedin_outreach.py

    # Same, then upsert the shortlist into the `recruiters` table:
    python scripts/linkedin_outreach.py --load

    # Point at a different export explicitly:
    python scripts/linkedin_outreach.py ~/Downloads/Connections.csv

The LinkedIn export starts with a 2-3 line "Notes:" preamble before the real
header row (First Name, Last Name, URL, Email Address, Company, Position,
Connected On), so we scan for the header rather than assuming row 0.
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from pipeline.sponsorship import is_known_sponsor, _normalize  # noqa: E402
from tracker.tracker import DB_PATH, init_db  # noqa: E402

# ── Role classification ────────────────────────────────────────────────────
# A connection's Position string is matched against these, first hit wins.
# The order encodes priority: a "Technical Recruiter, ML" is a relevant
# recruiter, not a generic one.

# NOTE: no trailing \b after the group — "recruit\b" would fail to match
# "recruiter"/"recruiting" (no word boundary between "recruit" and "er").
# Word stems (recruit\w*) handle recruiter/recruiting/recruits/recruited.
RECRUITER_RE = re.compile(
    r"\b(recruit\w*|talent|sourc\w*|staffing|headhunt\w*|people ops|"
    r"human resources|hr)\b",
    re.I,
)
# Signals that a recruiter/HM works the roles Ishani wants.
RELEVANT_CTX_RE = re.compile(
    r"\b(ai|ml|machine learning|deep learning|research|data scien\w*|"
    r"applied scien\w*|cloud|engineer\w*|technical|tech|software|university|"
    r"campus|early career|new ?grad|emerging talent|student|infrastructure|"
    r"platform)\b",
    re.I,
)
ENGINEER_RE = re.compile(
    r"\b(software engineer|swe\b|sde\b|\bmle\b|ml engineer|machine learning engineer|"
    r"applied scientist|research scientist|research engineer|data scientist|"
    r"member of technical staff|\bmts\b|developer|programmer|ai engineer|"
    r"deep learning|computer vision|nlp|robotics)\b",
    re.I,
)
MANAGER_RE = re.compile(
    r"\b(manager|director|\bhead\b|\blead\b|vp\b|vice president|principal|staff)\b",
    re.I,
)

# Role weights (leverage for a new-grad job search).
ROLE_WEIGHTS = {
    "recruiter_relevant": 3,   # recruiter on an AI/ML/eng/university team
    "engineer_referrer": 3,    # peer who can submit an internal referral
    "hiring_manager": 2,       # eng/ML manager — can refer or open a door
    "recruiter_generic": 1,    # recruiter, team unclear
    "other": 0,
}
# Company tiers. "applied" alone is NOT rare (201 applications across 202
# companies), so it's a light nudge tier, not the top. Interview-stage is the
# rare, high-value signal — a referral there could tip a live process.
TIER_INTERVIEW = "interview_stage"   # in an active interview/OA process there
TIER_SPONSOR = "known_sponsor"       # curated H-1B sponsor
TIER_APPLIED = "applied"             # applied, no further progress — warm nudge
TIER_OTHER = "other"


@dataclass
class Contact:
    first: str
    last: str
    url: str
    email: str
    company: str
    position: str
    connected_on: str
    role_type: str = "other"
    company_tier: str = TIER_OTHER
    company_weight: int = 0
    tier_label: str = ""
    score: int = 0

    @property
    def name(self) -> str:
        return f"{self.first} {self.last}".strip()


def classify_role(position: str) -> str:
    pos = position or ""
    is_recruiter = bool(RECRUITER_RE.search(pos))
    if is_recruiter:
        return "recruiter_relevant" if RELEVANT_CTX_RE.search(pos) else "recruiter_generic"
    if ENGINEER_RE.search(pos):
        return "engineer_referrer"
    if MANAGER_RE.search(pos) and RELEVANT_CTX_RE.search(pos):
        return "hiring_manager"
    return "other"


def load_company_signals(db_path: Path) -> tuple[set[str], set[str]]:
    """Normalized company-name sets from the tracker: (interview_stage, applied)."""
    try:
        conn = init_db(db_path)
    except Exception as e:  # noqa: BLE001 — DB is optional; degrade gracefully
        print(f"  (warning: could not open tracker DB — {e}; skipping DB tiers)")
        return set(), set()

    def _norm_set(rows) -> set[str]:
        return {_normalize(r["company"]) for r in rows if _normalize(r["company"])}

    interview = _norm_set(conn.execute(
        """
        SELECT DISTINCT company FROM jobs
        WHERE company IS NOT NULL AND TRIM(company) != ''
          AND (starred = 1
               OR status IN ('interview','interviewing','oa','onsite','phone_screen','offer'))
        """
    ).fetchall())
    applied = _norm_set(conn.execute(
        "SELECT DISTINCT company FROM jobs "
        "WHERE company IS NOT NULL AND TRIM(company) != '' AND status = 'applied'"
    ).fetchall())
    conn.close()
    return interview, applied


def company_signal(company: str, interview: set[str], applied: set[str]) -> tuple[str, int, str]:
    """Return (tier, weight, label). Applied+sponsor gets a small nudge bonus."""
    norm = _normalize(company)
    has_applied = norm in applied
    if norm in interview:
        return TIER_INTERVIEW, 4, "🎯 interview-stage"
    if is_known_sponsor(company):
        if has_applied:
            return TIER_SPONSOR, 4, "sponsor · applied"
        return TIER_SPONSOR, 3, "sponsor"
    if has_applied:
        return TIER_APPLIED, 2, "applied — nudge"
    return TIER_OTHER, 0, ""


def find_header_row(path: Path) -> int:
    """LinkedIn prepends a notes preamble; find the real CSV header row index."""
    with path.open(newline="", encoding="utf-8-sig") as f:
        for i, line in enumerate(f):
            if "First Name" in line and "Company" in line:
                return i
    raise ValueError(
        "Could not find the header row (expected 'First Name … Company'). "
        "Is this a LinkedIn Connections.csv export?"
    )


def read_contacts(path: Path) -> list[Contact]:
    skip = find_header_row(path)
    contacts: list[Contact] = []
    with path.open(newline="", encoding="utf-8-sig") as f:
        for _ in range(skip):
            next(f)
        reader = csv.DictReader(f)
        for row in reader:
            # Header names vary slightly across exports; normalize keys.
            g = {(k or "").strip().lower(): (v or "").strip() for k, v in row.items()}
            contacts.append(
                Contact(
                    first=g.get("first name", ""),
                    last=g.get("last name", ""),
                    url=g.get("url", ""),
                    email=g.get("email address", ""),
                    company=g.get("company", ""),
                    position=g.get("position", ""),
                    connected_on=g.get("connected on", ""),
                )
            )
    return contacts


def rank(contacts: list[Contact], interview: set[str], applied: set[str]) -> list[Contact]:
    for c in contacts:
        c.role_type = classify_role(c.position)
        c.company_tier, c.company_weight, c.tier_label = company_signal(
            c.company, interview, applied
        )
        c.score = c.company_weight + ROLE_WEIGHTS[c.role_type]
    # Primary list: relevant company AND some outreach value.
    shortlist = [
        c for c in contacts
        if c.company_tier != TIER_OTHER and c.role_type != "other"
    ]
    shortlist.sort(key=lambda c: (-c.score, c.company.lower(), c.name.lower()))
    return shortlist


ROLE_LABEL = {
    "recruiter_relevant": "Recruiter (relevant)",
    "engineer_referrer": "Engineer / referrer",
    "hiring_manager": "Hiring manager",
    "recruiter_generic": "Recruiter (generic)",
}


# ── LinkedIn referral-ask drafts ────────────────────────────────────────────
# These connections are all 1st-degree, so the play is a warm LinkedIn DM (not
# cold email) asking for a referral. Deterministic templates — personalized by
# the contact's first name, company, role type, and pipeline tier — so the run
# stays offline/fast; the report reminds you to tailor the top ones by hand.
# Sender identity is pulled from config/profile.json where practical, with these
# stable hooks as the fallback so the message reads right even without it.
SENDER_INTRO = (
    "I'm finishing my MS in Applied AI at Purdue and spent ~2 years as an SDE at "
    "AWS before this, now focused on new-grad AI/ML roles (RAG/LLM and applied ML)"
)


def draft_message(c: Contact) -> str:
    """A short, warm LinkedIn referral-ask DM tailored to one connection."""
    first = (c.first or c.name or "there").strip()
    company = (c.company or "your team").strip()

    # Context sentence — where this company sits in her funnel.
    if c.company_tier == TIER_INTERVIEW:
        ctx = f"I'm currently interviewing with {company} for an AI/ML role"
    elif c.company_tier == TIER_APPLIED:
        ctx = f"I recently applied to a few AI/ML roles at {company}"
    else:
        ctx = f"I'm focusing my search on AI/ML teams at {company}"

    # The ask — engineers/managers can refer; recruiters route you to the req.
    if c.role_type == "hiring_manager":
        ask = "Would you be open to referring me, or pointing me to the right person on your team?"
    elif c.role_type == "engineer_referrer":
        ask = "Would you be open to referring me internally?"
    else:  # recruiter_relevant / recruiter_generic
        ask = (f"Would you be the right person to talk to about new-grad AI/ML "
               f"openings at {company}, or could you point me to the team that's hiring?")

    return (
        f"Hi {first}, hope you've been well! {SENDER_INTRO}. "
        f"{ctx}. {ask} "
        f"Happy to send my resume and the exact job links to make it easy — "
        f"thanks so much either way!"
    )


def write_report(shortlist: list[Contact], all_contacts: list[Contact], out_dir: Path) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    md_path = out_dir / "linkedin_outreach.md"
    csv_path = out_dir / "linkedin_outreach.csv"

    n_recruiter = sum(1 for c in shortlist if c.role_type.startswith("recruiter"))
    n_eng = sum(1 for c in shortlist if c.role_type == "engineer_referrer")
    n_hm = sum(1 for c in shortlist if c.role_type == "hiring_manager")
    n_active = sum(1 for c in shortlist if c.company_tier == TIER_INTERVIEW)

    lines = [
        "# LinkedIn referral outreach — worklist",
        "",
        f"- **{len(all_contacts)}** connections scanned → **{len(shortlist)}** worth reaching out to",
        f"- {n_recruiter} recruiters · {n_eng} engineers/referrers · {n_hm} hiring managers",
        f"- {n_active} at companies where you're **interview-stage** (top priority)",
        "",
        "These are all 1st-degree connections, so message them **on LinkedIn** (not "
        "email). Ranked by leverage — work top-down and **personalize each draft** "
        "before sending (add a shared detail; don't paste as-is). Start with the "
        "interview-stage companies, then engineers/referrers at sponsors.",
        "",
        "---",
        "",
    ]
    for i, c in enumerate(shortlist, 1):
        profile = f"[LinkedIn profile]({c.url})" if c.url else "_(no profile URL)_"
        why = f" · {c.tier_label}" if c.tier_label else ""
        lines += [
            f"### {i}. {c.name} — {c.company}",
            f"_{c.position} · {ROLE_LABEL.get(c.role_type, c.role_type)}{why}_ · {profile}",
            "",
            f"> {draft_message(c)}",
            "",
        ]
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["rank", "name", "company", "title", "role_type",
                    "company_tier", "score", "linkedin_url", "message"])
        for i, c in enumerate(shortlist, 1):
            w.writerow([i, c.name, c.company, c.position, c.role_type,
                        c.company_tier, c.score, c.url, draft_message(c)])
    return md_path, csv_path


def load_into_db(shortlist: list[Contact], db_path: Path) -> tuple[int, int]:
    """Upsert the shortlist into `recruiters` (dedup by linkedin_url, else name+company)."""
    conn = init_db(db_path)
    inserted = updated = 0
    for c in shortlist:
        note = f"{ROLE_LABEL.get(c.role_type, c.role_type)} · {c.company_tier}"
        existing = None
        if c.url:
            existing = conn.execute(
                "SELECT id FROM recruiters WHERE linkedin_url = ?", (c.url,)
            ).fetchone()
        if existing is None:
            existing = conn.execute(
                "SELECT id FROM recruiters WHERE name = ? AND IFNULL(company,'') = ?",
                (c.name, c.company),
            ).fetchone()
        if existing:
            conn.execute(
                "UPDATE recruiters SET company=?, title=?, linkedin_url=COALESCE(NULLIF(?,''), linkedin_url), "
                "notes=? WHERE id=?",
                (c.company, c.position, c.url, note, existing["id"]),
            )
            updated += 1
        else:
            conn.execute(
                "INSERT INTO recruiters (name, email, company, title, linkedin_url, source, notes) "
                "VALUES (?,?,?,?,?, 'linkedin', ?)",
                (c.name, c.email or None, c.company, c.position, c.url, note),
            )
            inserted += 1
    conn.commit()
    conn.close()
    return inserted, updated


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv", type=Path, nargs="?",
                    default=REPO_ROOT / "data" / "linkedin" / "Connections.csv",
                    help="Path to LinkedIn Connections.csv "
                         "(default: data/linkedin/Connections.csv)")
    ap.add_argument("--load", action="store_true", help="Upsert the shortlist into the recruiters table")
    ap.add_argument("--out", type=Path, default=REPO_ROOT / "output" / "outreach",
                    help="Output directory for the report (default: output/outreach)")
    ap.add_argument("--db", type=Path, default=DB_PATH, help="Tracker DB path")
    args = ap.parse_args()

    if not args.csv.exists():
        print(f"error: {args.csv} not found", file=sys.stderr)
        return 1

    print(f"Reading {args.csv} …")
    contacts = read_contacts(args.csv)
    interview, applied = load_company_signals(args.db)
    if interview or applied:
        print(f"  {len(interview)} interview-stage companies (top tier) · "
              f"{len(applied)} applied-to companies (nudge tier)")
    shortlist = rank(contacts, interview, applied)

    md_path, csv_path = write_report(shortlist, contacts, args.out)
    print(f"  {len(contacts)} scanned → {len(shortlist)} on the shortlist")
    print(f"  report:  {md_path}")
    print(f"  csv:     {csv_path}")

    if args.load:
        ins, upd = load_into_db(shortlist, args.db)
        print(f"  loaded into recruiters: {ins} new, {upd} updated")
    else:
        print("  (dry run — pass --load to write into the recruiters table)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
