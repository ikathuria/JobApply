"""
SQLite-backed application tracker.
Stores every discovered job and tracks application status per listing.
"""

import sqlite3
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent / "applications.db"

STATUS_NEW = "new"               # discovered, not yet reviewed
STATUS_QUEUED = "queued"         # tailored, awaiting human review
STATUS_APPROVED = "approved"     # human approved — ready for GHA auto-apply
STATUS_SKIPPED = "skipped"       # manually skipped
STATUS_APPLIED = "applied"       # application submitted
STATUS_OA = "oa"                 # online assessment received
STATUS_INTERVIEW = "interview"   # interview scheduled
STATUS_REJECTED = "rejected"
STATUS_OFFER = "offer"

# Outreach record types + statuses (recruiters / referrals)
OUTREACH_COLD = "cold_email"
OUTREACH_REFERRAL = "referral"

OUTREACH_DRAFT = "draft"         # generated, not yet sent
OUTREACH_SENT = "sent"
OUTREACH_REPLIED = "replied"
OUTREACH_BOUNCED = "bounced"
OUTREACH_IGNORED = "ignored"     # no reply after follow-up window


def init_db(db_path: Path = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, check_same_thread=False, timeout=30)
    conn.row_factory = sqlite3.Row
    # WAL mode: readers never block writers and writers never block readers
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")  # safe + faster than FULL with WAL
    conn.commit()
    _create_tables(conn)
    return conn


def _create_tables(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS jobs (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            title           TEXT NOT NULL,
            company         TEXT,
            location        TEXT,
            url             TEXT UNIQUE NOT NULL,
            source_url      TEXT,
            source          TEXT,
            score           REAL DEFAULT 0.0,
            status          TEXT DEFAULT 'new',
            easy_apply      INTEGER DEFAULT 0,
            description     TEXT,
            date_scraped    TEXT,
            date_applied    TEXT,
            resume_path     TEXT,
            cover_letter    TEXT,
            notes           TEXT,
            rejection_stage TEXT    DEFAULT NULL,
            starred         INTEGER DEFAULT 0,
            interview_date  TEXT    DEFAULT NULL,
            recruiter       TEXT    DEFAULT NULL,
            salary_range    TEXT    DEFAULT NULL,
            follow_up_date  TEXT    DEFAULT NULL,
            created_at      TEXT DEFAULT (datetime('now')),
            updated_at      TEXT DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
        CREATE INDEX IF NOT EXISTS idx_jobs_score  ON jobs(score DESC);
        CREATE INDEX IF NOT EXISTS idx_jobs_source ON jobs(source);
    """)
    # Migrate existing DBs that pre-date any of these columns (ALTER TABLE
    # is a no-op if the column already exists — the exception is swallowed).
    for _col, _def in [
        ("source_url",      "TEXT"),
        ("rejection_stage", "TEXT DEFAULT NULL"),
        ("starred",         "INTEGER DEFAULT 0"),
        ("interview_date",  "TEXT DEFAULT NULL"),
        ("recruiter",       "TEXT DEFAULT NULL"),
        ("salary_range",    "TEXT DEFAULT NULL"),
        ("follow_up_date",  "TEXT DEFAULT NULL"),
    ]:
        try:
            conn.execute(f"ALTER TABLE jobs ADD COLUMN {_col} {_def}")
            conn.commit()
        except Exception:
            pass  # column already exists — expected for fresh and migrated DBs

    conn.execute("UPDATE jobs SET source_url = url WHERE COALESCE(source_url, '') = ''")
    try:
        conn.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_jobs_source_url_unique
            ON jobs(source_url)
            WHERE source_url IS NOT NULL AND source_url <> ''
            """
        )
        conn.commit()
    except Exception:
        pass

    # ── Outreach tables (recruiters + cold-email/referral tracking) ──────────
    # FKs are declarative only — referential integrity (cascade on recruiter
    # delete) is enforced in delete_recruiter(), because foreign_keys=ON isn't
    # set locally and Turso skips PRAGMAs, so DB-level enforcement would differ
    # between backends.
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS recruiters (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            name         TEXT NOT NULL,
            email        TEXT UNIQUE,
            company      TEXT,
            title        TEXT,
            linkedin_url TEXT,
            source       TEXT DEFAULT 'manual',
            notes        TEXT,
            created_at   TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS outreach (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            recruiter_id      INTEGER NOT NULL REFERENCES recruiters(id),
            job_id            INTEGER REFERENCES jobs(id),
            type              TEXT DEFAULT 'cold_email',
            subject           TEXT,
            body              TEXT,
            status            TEXT DEFAULT 'draft',
            sent_at           TEXT,
            reply_received_at TEXT,
            follow_up_date    TEXT,
            notes             TEXT,
            created_at        TEXT DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_outreach_recruiter ON outreach(recruiter_id);
        CREATE INDEX IF NOT EXISTS idx_outreach_status    ON outreach(status);
    """)
    conn.commit()


def upsert_jobs(conn: sqlite3.Connection, jobs: list[dict]) -> tuple[int, int]:
    """
    Insert new jobs; skip if URL already exists.
    Returns (inserted_count, skipped_count).
    """
    inserted = 0
    skipped = 0

    for job in jobs:
        source_url = job.get("source_url") or job.get("url", "")
        existing = conn.execute(
            "SELECT id FROM jobs WHERE url = ? OR source_url = ? LIMIT 1",
            (job.get("url", ""), source_url),
        ).fetchone()
        if existing:
            skipped += 1
            continue
        try:
            conn.execute(
                """
                INSERT INTO jobs (title, company, location, url, source_url, source, score,
                                  easy_apply, description, date_scraped, salary_range)
                VALUES (:title, :company, :location, :url, :source_url, :source, :score,
                        :easy_apply, :description, :date_scraped, :salary_range)
                """,
                {
                    "title": job.get("title", ""),
                    "company": job.get("company", ""),
                    "location": job.get("location", ""),
                    "url": job.get("url", ""),
                    "source_url": source_url,
                    "source": job.get("source", ""),
                    "score": job.get("score", 0.0),
                    "easy_apply": 1 if job.get("easy_apply") else 0,
                    "description": job.get("description", ""),
                    "date_scraped": job.get("date_scraped", datetime.utcnow().isoformat()),
                    "salary_range": job.get("salary_range") or job.get("salary", ""),
                },
            )
            inserted += 1
        except sqlite3.IntegrityError:
            skipped += 1  # URL already exists

    conn.commit()
    conn.execute("PRAGMA wal_checkpoint(PASSIVE)")  # flush WAL → main DB
    logger.info(f"Upserted jobs: {inserted} new, {skipped} already known.")
    return inserted, skipped


def get_jobs(
    conn: sqlite3.Connection,
    status: str | None = None,
    min_score: float = 0.0,
    limit: int = 200,
) -> list[sqlite3.Row]:
    query = "SELECT * FROM jobs WHERE score >= ?"
    params: list = [min_score]

    if status:
        query += " AND status = ?"
        params.append(status)

    query += " ORDER BY score DESC LIMIT ?"
    params.append(limit)

    return conn.execute(query, params).fetchall()


def update_status(conn: sqlite3.Connection, job_id: int, status: str, **kwargs) -> None:
    """Update a job's status and any optional fields (resume_path, notes, etc.)."""
    allowed = {
        "resume_path", "cover_letter", "notes", "date_applied",
        "starred", "interview_date", "recruiter", "salary_range",
        "follow_up_date", "rejection_stage",
        # direct-edit fields
        "title", "company", "location", "url", "source_url", "score", "description",
    }
    updates = {"status": status, "updated_at": datetime.utcnow().isoformat()}
    updates.update({k: v for k, v in kwargs.items() if k in allowed})

    set_clause = ", ".join(f"{k} = :{k}" for k in updates)
    updates["id"] = job_id

    conn.execute(f"UPDATE jobs SET {set_clause} WHERE id = :id", updates)
    conn.commit()
    conn.execute("PRAGMA wal_checkpoint(PASSIVE)")  # flush WAL → main DB


def get_stats(conn: sqlite3.Connection) -> dict:
    rows = conn.execute(
        "SELECT status, COUNT(*) as cnt FROM jobs GROUP BY status"
    ).fetchall()
    return {row["status"]: row["cnt"] for row in rows}


def already_applied(conn: sqlite3.Connection, url: str) -> bool:
    row = conn.execute(
        "SELECT status FROM jobs WHERE url = ?", (url,)
    ).fetchone()
    return row is not None and row["status"] == STATUS_APPLIED


# ── Recruiters CRUD ───────────────────────────────────────────────────────────

def _last_rowid(conn: sqlite3.Connection) -> int:
    """Cross-backend last insert id (works for sqlite3 and the Turso bridge)."""
    return conn.execute("SELECT last_insert_rowid()").fetchone()[0]


def _checkpoint(conn: sqlite3.Connection) -> None:
    conn.commit()
    try:
        conn.execute("PRAGMA wal_checkpoint(PASSIVE)")  # no-op on Turso
    except Exception:
        pass


def add_recruiter(
    conn: sqlite3.Connection,
    name: str,
    email: str | None = None,
    company: str | None = None,
    title: str | None = None,
    linkedin_url: str | None = None,
    source: str = "manual",
    notes: str | None = None,
) -> int:
    """Insert a recruiter; returns the new row id. Raises IntegrityError on
    duplicate email. Empty email is stored as NULL (allows multiple unknowns)."""
    conn.execute(
        """
        INSERT INTO recruiters (name, email, company, title, linkedin_url, source, notes)
        VALUES (:name, :email, :company, :title, :linkedin_url, :source, :notes)
        """,
        {
            "name": name,
            "email": (email or "").strip() or None,
            "company": company,
            "title": title,
            "linkedin_url": linkedin_url,
            "source": source,
            "notes": notes,
        },
    )
    _checkpoint(conn)
    return _last_rowid(conn)


def get_recruiter(conn: sqlite3.Connection, recruiter_id: int) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM recruiters WHERE id = ?", (recruiter_id,)
    ).fetchone()


def get_recruiter_by_email(conn: sqlite3.Connection, email: str) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM recruiters WHERE email = ?", ((email or "").strip(),)
    ).fetchone()


def list_recruiters(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """All recruiters with an outreach count + sent count, newest first."""
    return conn.execute(
        """
        SELECT r.*,
               COUNT(o.id) AS outreach_count,
               SUM(CASE WHEN o.status = 'sent' THEN 1 ELSE 0 END) AS sent_count
        FROM recruiters r
        LEFT JOIN outreach o ON o.recruiter_id = r.id
        GROUP BY r.id
        ORDER BY r.created_at DESC, r.id DESC
        """
    ).fetchall()


_RECRUITER_FIELDS = {"name", "email", "company", "title", "linkedin_url", "source", "notes"}


def update_recruiter(conn: sqlite3.Connection, recruiter_id: int, **fields) -> None:
    updates = {k: v for k, v in fields.items() if k in _RECRUITER_FIELDS}
    if not updates:
        return
    if "email" in updates:
        updates["email"] = (updates["email"] or "").strip() or None
    set_clause = ", ".join(f"{k} = :{k}" for k in updates)
    updates["id"] = recruiter_id
    conn.execute(f"UPDATE recruiters SET {set_clause} WHERE id = :id", updates)
    _checkpoint(conn)


def delete_recruiter(conn: sqlite3.Connection, recruiter_id: int) -> None:
    """Delete a recruiter and all their outreach rows (manual cascade)."""
    conn.execute("DELETE FROM outreach WHERE recruiter_id = ?", (recruiter_id,))
    conn.execute("DELETE FROM recruiters WHERE id = ?", (recruiter_id,))
    _checkpoint(conn)


# ── Outreach CRUD ─────────────────────────────────────────────────────────────

def add_outreach(
    conn: sqlite3.Connection,
    recruiter_id: int,
    type: str = OUTREACH_COLD,
    subject: str | None = None,
    body: str | None = None,
    job_id: int | None = None,
    status: str = OUTREACH_DRAFT,
) -> int:
    conn.execute(
        """
        INSERT INTO outreach (recruiter_id, job_id, type, subject, body, status)
        VALUES (:recruiter_id, :job_id, :type, :subject, :body, :status)
        """,
        {
            "recruiter_id": recruiter_id,
            "job_id": job_id,
            "type": type,
            "subject": subject,
            "body": body,
            "status": status,
        },
    )
    _checkpoint(conn)
    return _last_rowid(conn)


def get_outreach(conn: sqlite3.Connection, outreach_id: int) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM outreach WHERE id = ?", (outreach_id,)
    ).fetchone()


def list_outreach_for_recruiter(
    conn: sqlite3.Connection, recruiter_id: int
) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM outreach WHERE recruiter_id = ? ORDER BY created_at DESC, id DESC",
        (recruiter_id,),
    ).fetchall()


_OUTREACH_FIELDS = {
    "type", "subject", "body", "status",
    "sent_at", "reply_received_at", "follow_up_date", "notes", "job_id",
}


def update_outreach(conn: sqlite3.Connection, outreach_id: int, **fields) -> None:
    updates = {k: v for k, v in fields.items() if k in _OUTREACH_FIELDS}
    if not updates:
        return
    set_clause = ", ".join(f"{k} = :{k}" for k in updates)
    updates["id"] = outreach_id
    conn.execute(f"UPDATE outreach SET {set_clause} WHERE id = :id", updates)
    _checkpoint(conn)


def update_outreach_status(
    conn: sqlite3.Connection, outreach_id: int, status: str, **fields
) -> None:
    """Convenience wrapper: set status plus any other outreach fields."""
    update_outreach(conn, outreach_id, status=status, **fields)


def list_followups_due(conn: sqlite3.Connection, today: str) -> list[sqlite3.Row]:
    """Sent outreach whose follow-up date is on or before `today` (ISO date),
    joined with recruiter name/company — powers the follow-up reminder banner."""
    return conn.execute(
        """
        SELECT o.id, o.subject, o.sent_at, o.follow_up_date,
               r.id AS recruiter_id, r.name AS recruiter_name, r.company
        FROM outreach o
        JOIN recruiters r ON r.id = o.recruiter_id
        WHERE o.status = 'sent'
          AND o.follow_up_date IS NOT NULL
          AND o.follow_up_date <> ''
          AND o.follow_up_date <= ?
        ORDER BY o.follow_up_date ASC
        """,
        (today,),
    ).fetchall()
