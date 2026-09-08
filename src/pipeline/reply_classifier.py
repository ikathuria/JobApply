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

# Category → keyword phrases (matched over the full email unless noted).
_CATEGORIES = {
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

# Interview phrases split by how much context they need. STRONG phrases are
# specific enough to trust anywhere in the email; WEAK phrases ("hiring manager",
# "your availability") appear constantly in application-confirmation and process-
# description boilerplate, so they only count in the SUBJECT line — where a real
# invite actually announces itself. This is what keeps confirmation emails from
# being misread as interviews.
_INTERVIEW_STRONG = [
    "schedule an interview", "phone screen", "phone interview", "technical interview",
    "onsite interview", "on-site interview", "interview invitation", "coding interview",
    "would like to interview", "invite you to interview", "interview request",
    "schedule your interview", "invitation to interview",
]
_INTERVIEW_WEAK = [
    "video interview", "hiring manager", "next round", "your availability",
    "book a time", "meet with", "meet the team", "interview with", "recruiter call",
    "set up a call", "schedule a call", "schedule time", "interview",
]

# Affirmative offer phrases rejections never use — safe to match anywhere.
_OFFER_STRONG = [
    "pleased to offer", "we are excited to offer", "excited to offer you",
    "delighted to offer", "happy to offer you", "offer letter", "offer of employment",
    "we would like to offer you", "extend you an offer",
]
# Ambiguous offer wording ("extend an offer", "your offer") also shows up in
# rejections ("unable to extend an offer"), so only trust it in the SUBJECT.
_OFFER_SUBJECT = ["extend an offer", "your offer", "job offer", "offer from"]

# A confirmation SUBJECT is authoritative: the email is an acknowledgement that
# you applied, and its body typically *describes the whole funnel* ("we'll
# schedule an interview… we may extend an offer…") — which must NOT be read as a
# real interview/offer. Only a rejection body overrides a confirmation subject.
_CONFIRM_SUBJECT = [
    "thank you for applying", "thanks for applying", "thank you for your application",
    "thanks for your application", "application received", "we received your application",
    "confirmation of application", "confirmation of your application",
    "application submitted", "application confirmation", "your application was sent to",
    "we got your resume", "application to",  # LinkedIn "your application to ROLE at CO"
]

# Weaker confirmation signals used as a last-resort (body-level) fallback.
_CONFIRMATION = _CONFIRM_SUBJECT + [
    "we've received your application", "successfully submitted", "applying to",
    "received your application", "your application for",
]


def _hits(text: str, phrases) -> int:
    return sum(1 for kw in phrases if kw in text)


def classify(subject: str, body: str) -> str:
    """Return one of: applied, offer, interview, oa, rejection, other.

    Precedence (precision-biased for confirmation-heavy inboxes):
      1. explicit rejection language (body) — authoritative
      2. a confirmation SUBJECT → applied (ignore process boilerplate in the body)
      3. OA / interview / offer signals
      4. a confirmation anywhere → applied
      5. other
    """
    subject_l = (subject or "").lower()
    text = f"{subject or ''}\n{body or ''}".lower()

    if _hits(text, _CATEGORIES["rejection"]) > 0:
        return "rejection"
    if any(c in subject_l for c in _CONFIRM_SUBJECT):
        return "applied"

    if _hits(text, _CATEGORIES["oa"]) > 0:
        return "oa"
    interview = (_hits(text, _INTERVIEW_STRONG)
                 + _hits(subject_l, _INTERVIEW_WEAK))
    if interview > 0:
        return "interview"
    if _hits(text, _OFFER_STRONG) > 0 or _hits(subject_l, _OFFER_SUBJECT) > 0:
        return "offer"

    if any(c in text for c in _CONFIRMATION):
        return "applied"
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
    if category == "applied":
        cur = STATUS_RANK.get(current_status, -1)
        return "applied" if cur < STATUS_RANK["applied"] else None
    if category in ("oa", "interview", "offer"):
        cur = STATUS_RANK.get(current_status, -1)
        new = STATUS_RANK.get(category, -1)
        return category if new > cur else None
    return None
