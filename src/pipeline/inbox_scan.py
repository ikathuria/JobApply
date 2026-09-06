"""
Scan the mailbox and auto-advance job statuses from recruiter replies.

Ties together inbox_reader (IMAP fetch), reply_classifier (classify + match +
decide), the tracker (status update), and notifications (milestone email). It is
precision-biased: it only changes a status when an email clearly maps to exactly
one active job and represents a genuine forward transition (or a rejection of an
active application). Everything else is reported but left untouched.

Run: ``python main.py --scan-inbox [--limit N]``
"""

import logging
from pathlib import Path

import yaml

from pipeline import reply_classifier as rc
from tracker.tracker import update_status

logger = logging.getLogger(__name__)

_SETTINGS_PATH = Path("config/settings.yaml")
_ACTIVE_STATUSES = ("queued", "approved", "applied", "oa", "interview")


def _load_settings() -> dict:
    try:
        return yaml.safe_load(_SETTINGS_PATH.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        return {}


def _active_jobs(conn) -> list[dict]:
    placeholders = ",".join("?" for _ in _ACTIVE_STATUSES)
    rows = conn.execute(
        f"SELECT * FROM jobs WHERE status IN ({placeholders}) "
        f"AND COALESCE(company,'') <> ''",
        _ACTIVE_STATUSES,
    ).fetchall()
    return [dict(r) for r in rows]


def _pick_job(jobs: list[dict], company: str) -> dict | None:
    """Best active job for a company: the furthest-along, most-recently-touched."""
    matches = [j for j in jobs if j.get("company") == company]
    if not matches:
        return None
    matches.sort(
        key=lambda j: (
            rc.STATUS_RANK.get(j.get("status"), -1),
            j.get("date_applied") or j.get("updated_at") or "",
        ),
        reverse=True,
    )
    return matches[0]


def scan_inbox(conn, limit: int = 40, days: int = 30, notify: bool = True) -> dict:
    """Fetch recent mail and apply confident status transitions.

    Returns a summary dict::

        {
          "scanned": int,
          "updated": [ {job_id, company, title, from, category, old, new} ],
          "matched_no_change": [ {company, category, status} ],
          "unmatched": [ {from, subject, category} ],   # classified but no job
        }
    """
    from pipeline.inbox_reader import fetch_recent

    messages = fetch_recent(limit=limit, days=days)
    jobs = _active_jobs(conn)
    companies = sorted({j["company"] for j in jobs if j.get("company")})
    settings = _load_settings()

    summary = {"scanned": len(messages), "updated": [],
               "matched_no_change": [], "unmatched": []}

    for msg in messages:
        category = rc.classify(msg.get("subject", ""), msg.get("body", ""))
        if category == "other":
            continue

        company = rc.match_company(
            f"{msg.get('subject', '')} {msg.get('body', '')}",
            msg.get("from", ""), companies,
        )
        if not company:
            summary["unmatched"].append({
                "from": msg.get("from", ""), "subject": msg.get("subject", ""),
                "category": category,
            })
            continue

        job = _pick_job(jobs, company)
        if not job:
            summary["matched_no_change"].append(
                {"company": company, "category": category, "status": "no-active-job"})
            continue

        new_status = rc.decide_transition(job.get("status"), category)
        if not new_status:
            summary["matched_no_change"].append(
                {"company": company, "category": category, "status": job.get("status")})
            continue

        old = job.get("status")
        update_status(conn, job["id"], new_status)
        job["status"] = new_status  # keep local copy in sync for repeat senders
        summary["updated"].append({
            "job_id": job["id"], "company": company, "title": job.get("title"),
            "from": msg.get("from", ""), "category": category,
            "old": old, "new": new_status,
        })
        if notify:
            try:
                from pipeline.notifications import notify_status_change
                notify_status_change(job, new_status, settings)
            except Exception as e:
                logger.warning(f"notify failed for job {job['id']}: {e}")

    return summary


def print_summary(summary: dict) -> None:
    print(f"\n-- Inbox scan: {summary['scanned']} message(s) ------------------")
    if summary["updated"]:
        print(f"  Updated {len(summary['updated'])} job(s):")
        for u in summary["updated"]:
            print(f"    • {u['company']} — {u['title']}: {u['old']} → {u['new'].upper()} "
                  f"({u['category']})")
    else:
        print("  No status changes.")
    if summary["unmatched"]:
        print(f"  {len(summary['unmatched'])} classified email(s) with no matching job "
              f"(review manually):")
        for m in summary["unmatched"][:10]:
            print(f"    ? [{m['category']}] {m['subject'][:60]} — {m['from'][:40]}")
    print()
