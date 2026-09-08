"""
Scan the mailbox and reconstruct / advance the job funnel from email.

Two modes:

* **update** (default) — read the "reverts" folder and advance jobs the tracker
  already knows you applied to (OA / interview / rejection / offer). Precision-
  biased: it only acts on a clear category + exactly one matching active job +
  a genuine forward transition; everything else is reported, not touched.

* **ingest** (``--ingest``) — also read the "job apps" folder and *create* a
  tracked application for every company that emailed you, then advance it. This
  reconstructs your whole real funnel from the mailbox when you apply outside
  the tool. Applications are keyed by normalized company (one record per
  company), created at ``applied`` with the email's date, and never duplicated
  on re-runs.

Folders come from env (``IMAP_APPLIED_MAILBOX`` default "INBOX.job apps",
``IMAP_REVERTS_MAILBOX`` / ``IMAP_MAILBOX`` default "INBOX"). Run:

    python main.py --scan-inbox            # advance tracked jobs
    python main.py --scan-inbox --ingest   # reconstruct the funnel from mail
"""

import logging
import os
import re
from datetime import date
from pathlib import Path

import yaml

from pipeline import reply_classifier as rc
from pipeline.application_parser import parse as parse_application
from pipeline.reply_classifier import _norm as _norm_company
from tracker.tracker import STATUS_APPLIED, update_status, upsert_jobs

logger = logging.getLogger(__name__)

_SETTINGS_PATH = Path("config/settings.yaml")
_ACTIVE_STATUSES = ("queued", "approved", "applied", "oa", "interview")


def _load_settings() -> dict:
    try:
        return yaml.safe_load(_SETTINGS_PATH.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        return {}


def _default_folders(ingest: bool) -> list[str]:
    reverts = (os.getenv("IMAP_REVERTS_MAILBOX") or os.getenv("IMAP_MAILBOX") or "INBOX").strip()
    folders = [reverts]
    if ingest:
        applied = (os.getenv("IMAP_APPLIED_MAILBOX") or "INBOX.job apps").strip()
        if applied and applied != reverts:
            folders = [applied, reverts]  # confirmations first, then responses
    return folders


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")[:60]


def _email_snippet(msg: dict) -> str:
    """A compact, readable record of one email for the job's description."""
    body = (msg.get("body") or "").strip()
    body = re.sub(r"[ \t]+\n", "\n", body)
    body = re.sub(r"\n{3,}", "\n\n", body)[:2000]
    date = (msg.get("date") or "")[:10]
    header = f"── {date} · {msg.get('subject', '(no subject)')}".strip()
    return f"{header}\nFrom: {msg.get('from', '')}\n\n{body}".strip()


def _attach_email(conn, job: dict, msg: dict) -> None:
    """Append this email to the job's description (email-sourced jobs only), so
    the tracked application carries the actual message. Idempotent per subject."""
    if job.get("source") != "email":
        return  # never clobber a scraped job's real JD
    subject = (msg.get("subject") or "").strip()
    existing = job.get("description") or ""
    if subject and subject in existing:
        return  # already attached on a previous message / run
    snippet = _email_snippet(msg)
    new_desc = (existing + "\n\n" + snippet).strip() if existing else snippet
    new_desc = new_desc[:12000]
    update_status(conn, job["id"], job.get("status"), description=new_desc)
    job["description"] = new_desc


def _jobs(conn, statuses) -> list[dict]:
    if statuses is None:
        rows = conn.execute("SELECT * FROM jobs WHERE COALESCE(company,'') <> ''").fetchall()
    else:
        ph = ",".join("?" for _ in statuses)
        rows = conn.execute(
            f"SELECT * FROM jobs WHERE status IN ({ph}) AND COALESCE(company,'') <> ''", statuses
        ).fetchall()
    return [dict(r) for r in rows]


def _index_by_company(jobs: list[dict]) -> dict[str, dict]:
    """Map normalized company → the furthest-along job for that company."""
    idx: dict[str, dict] = {}
    for j in jobs:
        norm = _norm_company(j.get("company", ""))
        if not norm:
            continue
        cur = idx.get(norm)
        if cur is None or rc.STATUS_RANK.get(j.get("status"), -1) > rc.STATUS_RANK.get(cur.get("status"), -1):
            idx[norm] = j
    return idx


def _create_application(conn, company: str, role: str | None, applied_date: str | None) -> dict:
    """Create a synthetic 'applied' job for an email-only application (idempotent
    on the synthetic URL). Returns the job row as a dict."""
    url = f"email:{_slug(company)}"
    upsert_jobs(conn, [{
        "title": role or "(applied via email)",
        "company": company,
        "url": url,
        "source": "email",
        "status": STATUS_APPLIED,
        "date_scraped": applied_date or "",
    }])
    row = conn.execute("SELECT * FROM jobs WHERE url = ?", (url,)).fetchone()
    job = dict(row)
    # upsert_jobs skips if the URL already exists, so set the applied date only
    # when we actually just created it (no date_applied yet).
    if not job.get("date_applied"):
        update_status(conn, job["id"], job["status"],
                      date_applied=applied_date or date.today().isoformat())
        job["date_applied"] = applied_date or date.today().isoformat()
    return job


def scan_inbox(conn, limit: int = 60, days: int = 60, notify: bool = True,
               ingest: bool = False, folders: list[str] | None = None) -> dict:
    """Fetch mail and apply confident status transitions (see module docstring)."""
    from pipeline.inbox_reader import fetch_recent

    folders = folders if folders is not None else _default_folders(ingest)
    messages: list[dict] = []
    for folder in folders:
        messages.extend(fetch_recent(limit=limit, days=days, mailbox=folder))

    jobs = _jobs(conn, None if ingest else _ACTIVE_STATUSES)
    by_company = _index_by_company(jobs)
    companies = sorted({j["company"] for j in jobs if j.get("company")})
    settings = _load_settings()

    summary = {"scanned": len(messages), "folders": folders, "updated": [],
               "created": [], "matched_no_change": [], "unmatched": []}

    for msg in messages:
        category = rc.classify(msg.get("subject", ""), msg.get("body", ""))
        if category == "other":
            continue

        text = f"{msg.get('subject', '')} {msg.get('body', '')}"
        company = rc.match_company(text, msg.get("from", ""), companies)
        job = by_company.get(_norm_company(company)) if company else None

        if job is None and ingest:
            parsed = parse_application(msg.get("subject", ""), msg.get("from", ""))
            if not parsed["company"]:
                summary["unmatched"].append({"from": msg.get("from", ""),
                                             "subject": msg.get("subject", ""),
                                             "category": category})
                continue
            job = _create_application(conn, parsed["company"], parsed["role"],
                                      (msg.get("date") or "")[:10] or None)
            by_company[_norm_company(parsed["company"])] = job
            if parsed["company"] not in companies:
                companies.append(parsed["company"])
            summary["created"].append({"job_id": job["id"], "company": parsed["company"],
                                       "title": job.get("title"), "category": category})

        if job is None:
            summary["unmatched"].append({"from": msg.get("from", ""),
                                         "subject": msg.get("subject", ""),
                                         "category": category})
            continue

        # Keep the actual email on the tracked application (email-sourced only).
        _attach_email(conn, job, msg)

        new_status = rc.decide_transition(job.get("status"), category)
        if not new_status:
            summary["matched_no_change"].append({"company": job.get("company"),
                                                 "category": category,
                                                 "status": job.get("status")})
            continue

        old = job.get("status")
        kwargs = {}
        if new_status == STATUS_APPLIED:
            kwargs["date_applied"] = (msg.get("date") or "")[:10] or date.today().isoformat()
        update_status(conn, job["id"], new_status, **kwargs)
        job["status"] = new_status
        summary["updated"].append({"job_id": job["id"], "company": job.get("company"),
                                   "title": job.get("title"), "from": msg.get("from", ""),
                                   "category": category, "old": old, "new": new_status})
        if notify:
            try:
                from pipeline.notifications import notify_status_change
                notify_status_change(job, new_status, settings)
            except Exception as e:
                logger.warning(f"notify failed for job {job['id']}: {e}")

    return summary


def print_summary(summary: dict) -> None:
    print(f"\n-- Inbox scan: {summary['scanned']} message(s) from "
          f"{', '.join(summary['folders'])} ------------")
    if summary.get("created"):
        print(f"  Tracked {len(summary['created'])} new application(s) from email.")
    if summary["updated"]:
        print(f"  Updated {len(summary['updated'])} job(s):")
        for u in summary["updated"]:
            print(f"    • {u['company']} — {u['title']}: {u['old']} → {u['new'].upper()} "
                  f"({u['category']})")
    if not summary["updated"] and not summary.get("created"):
        print("  No status changes.")
    if summary["unmatched"]:
        print(f"  {len(summary['unmatched'])} classified email(s) with no company match:")
        for m in summary["unmatched"][:10]:
            print(f"    ? [{m['category']}] {m['subject'][:55]} — {m['from'][:35]}")
    print()
