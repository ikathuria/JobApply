"""
One-time script: upsert local SQLite → Turso (local is source of truth).
Uses INSERT OR REPLACE so no full wipe needed — handles timeouts gracefully.
Run from repo root: python scripts/force_reseed_turso.py
"""
import os
import sqlite3
import sys
import time
from pathlib import Path

# Load .env
env_file = Path(__file__).parent.parent / ".env"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())

sys.path.insert(0, str(Path(__file__).parent.parent))

import requests as _req

# Patch requests timeout globally to 60s
_orig_post = _req.post
def _post_long(*a, **kw):
    kw["timeout"] = 60
    return _orig_post(*a, **kw)
_req.post = _post_long

from api.turso import connect

SQLITE_PATH = Path(__file__).parent.parent / "tracker" / "applications.db"
BATCH = 10  # small batches to avoid timeouts

def main():
    print(f"Connecting to Turso: {os.environ['TURSO_DATABASE_URL']}")
    turso = connect()

    before = turso.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
    print(f"Turso currently has {before} rows")

    # Read local SQLite
    if not SQLITE_PATH.exists():
        print(f"ERROR: local DB not found at {SQLITE_PATH}")
        sys.exit(1)

    src = sqlite3.connect(str(SQLITE_PATH))
    src.row_factory = sqlite3.Row
    jobs = [dict(r) for r in src.execute("SELECT * FROM jobs").fetchall()]
    local_urls = {j["url"] for j in jobs}
    src.close()
    print(f"Local SQLite has {len(jobs)} rows — upserting to Turso...")

    # INSERT OR REPLACE upserts all local rows (overwrites Turso with local state)
    cols = [c for c in jobs[0].keys() if c != "id"]
    placeholders = ", ".join("?" * len(cols))
    col_names = ", ".join(cols)
    sql = f"INSERT OR REPLACE INTO jobs ({col_names}) VALUES ({placeholders})"

    ok = fail = 0
    for i in range(0, len(jobs), BATCH):
        batch = jobs[i : i + BATCH]
        stmts = []
        for job in batch:
            args = [turso._to_arg(job.get(c)) for c in cols]
            stmts.append({"type": "execute", "stmt": {"sql": sql, "args": args}})
        stmts.append({"type": "close"})

        retries = 3
        for attempt in range(retries):
            try:
                results = turso._pipeline(stmts)
                for r in results:
                    if r.get("type") == "error":
                        fail += 1
                    elif r.get("type") == "ok":
                        ok += 1
                break
            except Exception as e:
                if attempt < retries - 1:
                    print(f"  batch {i // BATCH + 1} attempt {attempt + 1} failed ({e}), retrying...")
                    time.sleep(2)
                else:
                    fail += len(batch)
                    print(f"  batch {i // BATCH + 1} failed after {retries} attempts: {e}")

        if (i // BATCH + 1) % 10 == 0:
            print(f"  progress: {i + len(batch)}/{len(jobs)} rows...")

    print(f"\nUpsert done — {ok} ok, {fail} failed")

    # Delete Turso rows not present in local (stale rows)
    turso_ids = turso.execute("SELECT id, url FROM jobs").fetchall()
    stale = [r[0] for r in turso_ids if r[1] not in local_urls]
    if stale:
        print(f"Deleting {len(stale)} stale Turso-only rows...")
        removed = 0
        for job_id in stale:
            try:
                turso.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
                removed += 1
            except Exception as e:
                print(f"  could not delete id {job_id}: {e}")
        print(f"  removed {removed} stale rows")
    else:
        print("No stale rows to remove")

    final = turso.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
    print(f"\nFinal Turso count: {final} rows (local: {len(jobs)})")

if __name__ == "__main__":
    main()
