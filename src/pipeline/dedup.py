"""
Detect duplicate job listings that arrive from multiple sources.

The same role often shows up via intern-list, newgrad-jobs, and Jobright with
slightly different titles/URLs. This groups NEW listings by normalized
(company, title), keeps the highest-scored one per group, and marks the rest
``skipped`` with a note pointing at the keeper. It only ever touches ``new``
jobs, so nothing you've queued/applied to is disturbed, and it's reversible
(status change, not deletion).
"""

import logging
import re

from tracker.tracker import STATUS_NEW, STATUS_SKIPPED, update_status
from pipeline.reply_classifier import _norm as _norm_company

logger = logging.getLogger(__name__)

# Noise stripped from titles before comparison.
_TITLE_NOISE = re.compile(
    r"\b(20\d\d|summer|fall|spring|winter|intern(ship)?|co-?op|new\s*grad(uate)?|"
    r"entry\s*level|early\s*career|university|remote|hybrid|onsite|us|usa)\b",
    re.I,
)


def _norm_title(title: str) -> str:
    t = (title or "").lower()
    t = _TITLE_NOISE.sub(" ", t)
    t = re.sub(r"[^a-z0-9 ]+", " ", t)
    return " ".join(t.split())


def _key(job: dict) -> str:
    return f"{_norm_company(job.get('company', ''))}|{_norm_title(job.get('title', ''))}"


def find_duplicate_groups(jobs: list[dict]) -> list[list[dict]]:
    """Group jobs by normalized (company, title). Returns only groups with >1
    member, each sorted best-first (highest score, then lowest id)."""
    buckets: dict[str, list[dict]] = {}
    for job in jobs:
        key = _key(job)
        # An empty company or title normalizes to a near-empty key — never group
        # those together (would collapse unrelated listings).
        if key.strip("|") == "":
            continue
        buckets.setdefault(key, []).append(job)

    groups = []
    for members in buckets.values():
        if len(members) < 2:
            continue
        members.sort(key=lambda j: (-(j.get("score") or 0.0), j.get("id") or 0))
        groups.append(members)
    return groups


def dedup_new_jobs(conn) -> list[list[dict]]:
    """Find duplicate NEW listings and skip all but the best in each group.

    Returns the duplicate groups (keeper first). Only ``new`` jobs are considered
    and modified.
    """
    rows = conn.execute(
        "SELECT * FROM jobs WHERE status = ?", (STATUS_NEW,)
    ).fetchall()
    jobs = [dict(r) for r in rows]
    groups = find_duplicate_groups(jobs)

    for group in groups:
        keeper = group[0]
        for dup in group[1:]:
            note = (dup.get("notes") or "").strip()
            tag = f"duplicate of #{keeper['id']} ({keeper.get('title', '')})"
            new_note = f"{note}\n{tag}".strip() if note else tag
            update_status(conn, dup["id"], STATUS_SKIPPED, notes=new_note)
            logger.info(f"Skipped dup job #{dup['id']} → keeper #{keeper['id']}")
    return groups
