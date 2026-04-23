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


def upsert_jobs(conn: sqlite3.Connection, jobs: list[dict]) -> tuple[int, int]:
    """
    Insert new jobs; skip if URL already exists.
    Returns (inserted_count, skipped_count).
    """
    inserted = 0
    skipped = 0

    for job in jobs:
        try:
            conn.execute(
                """
                INSERT INTO jobs (title, company, location, url, source, score,
                                  easy_apply, description, date_scraped)
                VALUES (:title, :company, :location, :url, :source, :score,
                        :easy_apply, :description, :date_scraped)
                """,
                {
                    "title": job.get("title", ""),
                    "company": job.get("company", ""),
                    "location": job.get("location", ""),
                    "url": job.get("url", ""),
                    "source": job.get("source", ""),
                    "score": job.get("score", 0.0),
                    "easy_apply": 1 if job.get("easy_apply") else 0,
                    "description": job.get("description", ""),
                    "date_scraped": job.get("date_scraped", datetime.utcnow().isoformat()),
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
        "title", "company", "location", "url", "score",
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
