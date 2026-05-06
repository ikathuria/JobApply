"""
Pull all rows from Turso into local SQLite (Turso → local).
Run from repo root: python scripts/pull_from_turso.py
"""
import os
import sqlite3
import sys
import time
from pathlib import Path

env_file = Path(__file__).parent.parent / ".env"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())

sys.path.insert(0, str(Path(__file__).parent.parent))

import requests as _req
_orig_post = _req.post
def _post_long(*a, **kw):
    kw["timeout"] = 60
    return _orig_post(*a, **kw)
_req.post = _post_long

from api.turso import connect

SQLITE_PATH = Path(__file__).parent.parent / "tracker" / "applications.db"
BATCH = 100

def main():
    print(f"Connecting to Turso...")
    turso = connect()

    total = turso.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
    print(f"Turso has {total} rows — fetching in batches...")

    all_jobs = []
    offset = 0
    while True:
        rows = turso.execute(
            f"SELECT * FROM jobs ORDER BY id LIMIT {BATCH} OFFSET {offset}"
        ).fetchall()
        if not rows:
            break
        all_jobs.extend([dict(r) for r in rows])
        offset += len(rows)
        print(f"  fetched {offset}/{total}...")

    print(f"\nFetched {len(all_jobs)} rows from Turso")
    print(f"Writing to {SQLITE_PATH}...")

    conn = sqlite3.connect(str(SQLITE_PATH))
    conn.row_factory = sqlite3.Row

    cols = [c for c in all_jobs[0].keys() if c != "id"]
    col_names = ", ".join(cols)
    placeholders = ", ".join("?" * len(cols))
    sql = f"INSERT OR REPLACE INTO jobs ({col_names}) VALUES ({placeholders})"

    ok = fail = 0
    for job in all_jobs:
        try:
            conn.execute(sql, [job.get(c) for c in cols])
            ok += 1
        except Exception as e:
            fail += 1
            print(f"  row {job.get('id')} failed: {e}")

    conn.commit()
    conn.execute("PRAGMA wal_checkpoint(PASSIVE)")
    conn.close()

    local_total = sqlite3.connect(str(SQLITE_PATH)).execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
    print(f"\nDone — local SQLite now has {local_total} rows ({fail} failed)")

if __name__ == "__main__":
    main()
