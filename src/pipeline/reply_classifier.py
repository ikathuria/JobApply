"""
Classify recruiting emails and match them to a tracked job.

Pure, deterministic keyword logic (no LLM, no network) so it's fast, free, and
unit-testable. The scanner (inbox_scan.py) uses this to decide whether an email
represents a real status transition and, if so, which job it belongs to.

Design bias: **precision over recall.** A wrong auto-update (e.g. flipping a job
to "rejected" off a newsletter) is worse than missing one, so ambiguous emails
resolve to ``other`` / no match and are left for the human.
"""

import re

# Category → ordered keyword phrases. Longer, more specific phrases first.
_CATEGORIES = {
    "offer": [
        "pleased to offer", "offer letter", "we are excited to offer",
        "extend an offer", "your offer", "job offer",
    ],
    "interview": [
        "schedule an interview", "schedule a call", "phone screen", "phone interview",
        "technical interview", "onsite interview", "video interview", "hiring manager",
        "next round", "next steps", "your availability", "book a time", "meet with",
        "interview with", "recruiter call", "interview invitation", "set up a call",
    ],
    "oa": [
        "online assessment", "coding assessment", "coding challenge", "coding test",
        "take-home", "take home", "hackerrank", "codesignal", "coderpad", "codility",
        "technical assessment", "complete the assessment", "skills assessment",
    ],
    "rejection": [
        "regret to inform", "not moving forward", "will not be moving forward",
        "not be moving forward", "decided not to proceed", "will not be proceeding",
        "no longer under consideration", "other candidates", "other applicants",
        "not to move forward", "unfortunately, we", "unfortunately we",
        "position has been filled", "pursue other candidates", "wish you the best",
        "we have decided to move forward with",
    ],
}

# Tie-break priority when two categories score equally.
_PRIORITY = ["offer", "rejection", "interview", "oa"]

# Confirmation/no-op signals — treated as `other` even if other keywords appear.
_CONFIRMATION = [
    "thank you for applying", "application received", "we received your application",
    "thanks for applying", "successfully submitted",
]


def classify(subject: str, body: str) -> str:
    """Return one of: offer, interview, oa, rejection, other."""
    text = f"{subject or ''}\n{body or ''}".lower()

    # A pure "we got your application" confirmation with no stronger signal is noise.
    if any(c in text for c in _CONFIRMATION):
        strong = any(
            kw in text
            for cat in ("offer", "interview", "oa", "rejection")
            for kw in _CATEGORIES[cat]
        )
        if not strong:
            return "other"

    scores = {
        cat: sum(1 for kw in kws if kw in text)
        for cat, kws in _CATEGORIES.items()
    }
    best = max(scores.values())
    if best == 0:
        return "other"
    winners = [cat for cat, s in scores.items() if s == best]
    if len(winners) == 1:
        return winners[0]
    for cat in _PRIORITY:
        if cat in winners:
            return cat
    return "other"


def _norm(name: str) -> str:
    """Normalize a company name to comparable tokens (drop Inc/LLC/punctuation)."""
    name = (name or "").lower()
    name = re.sub(r"[^a-z0-9 ]+", " ", name)
    stop = {"inc", "llc", "ltd", "corp", "co", "the", "company", "technologies",
            "labs", "ai", "io"}
    return " ".join(t for t in name.split() if t and t not in stop)


def match_company(text: str, from_addr: str, companies: list[str]) -> str | None:
    """Return the single company from ``companies`` mentioned in the email, or None.

    Matches on the email body/subject and the sender domain. Returns None when
    zero or more than one distinct company matches (ambiguous → leave to human).
    """
    haystack = f"{text or ''} {from_addr or ''}".lower()
    domain = ""
    m = re.search(r"@([a-z0-9.\-]+)", (from_addr or "").lower())
    if m:
        domain = m.group(1)

    hits = set()
    for comp in companies:
        norm = _norm(comp)
        if not norm:
            continue
        tokens = norm.split()
        # Match if the full normalized name (or its distinctive first token, len>=4)
        # appears in the text, or the domain contains it.
        head = tokens[0]
        candidates = {norm}
        if len(head) >= 4:
            candidates.add(head)
        if any(c in haystack for c in candidates) or (head and len(head) >= 4 and head in domain):
            hits.add(comp)

    return next(iter(hits)) if len(hits) == 1 else None


# Status rank for forward-only transitions (rejection handled separately).
STATUS_RANK = {
    "new": 0, "queued": 1, "approved": 2, "applied": 3,
    "oa": 4, "interview": 5, "offer": 6,
}
_ACTIVE_FOR_REJECTION = {"applied", "oa", "interview", "queued", "approved"}


def decide_transition(current_status: str, category: str) -> str | None:
    """Given a job's current status and an email category, return the new status
    to set, or None to leave it unchanged.

    Only advances forward (never regresses an OA back to applied); rejection can
    apply from any active, non-terminal state.
    """
    if category == "rejection":
        return "rejected" if current_status in _ACTIVE_FOR_REJECTION else None
    if category in ("oa", "interview", "offer"):
        cur = STATUS_RANK.get(current_status, -1)
        new = STATUS_RANK.get(category, -1)
        return category if new > cur else None
    return None
