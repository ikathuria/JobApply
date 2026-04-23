"""
Pure-Python Turso adapter using the Turso HTTP API.
No Rust, no native compilation — just requests.

Used automatically by api/main.py when TURSO_DATABASE_URL is set.
"""

from __future__ import annotations
import os
import sqlite3
from pathlib import Path
from typing import Any

import requests as _requests


# ── Row wrapper ───────────────────────────────────────────────────────────────

class _DictRow:
    """Dict- and index-accessible row, mimics sqlite3.Row."""
    __slots__ = ("_d", "_v")

    def __init__(self, keys: list[str], values: list):
        self._v = list(values)
        self._d = dict(zip(keys, values))

    def __getitem__(self, key):
        return self._v[key] if isinstance(key, int) else self._d[key]

    def get(self, key, default=None):
        return self._d.get(key, default)

    def keys(self):
        return self._d.keys()

    def __iter__(self):
        return iter(self._v)

    def __repr__(self):
        return repr(self._d)


# ── Cursor wrappers ───────────────────────────────────────────────────────────

class _EmptyCursor:
    description = None
    lastrowid   = None
    def fetchone(self):  return None
    def fetchall(self):  return []


class _StaticCursor:
    """Holds rows already fetched from the HTTP response."""

    def __init__(self, cols: list[str], rows: list[_DictRow], lastrowid=None):
        self._rows    = rows
        self._pos     = 0
        self.lastrowid   = lastrowid
        self.description = [(c, None, None, None, None, None, None) for c in cols]

    def fetchone(self):
        if self._pos >= len(self._rows):
            return None
        row = self._rows[self._pos]
        self._pos += 1
        return row

    def fetchall(self):
        rows = self._rows[self._pos:]
        self._pos = len(self._rows)
        return rows


# ── HTTP connection ───────────────────────────────────────────────────────────

class TursoConn:
    """
    sqlite3.Connection-compatible wrapper that talks to Turso over HTTPS.

    Handles:
    - row_factory setter → no-op
    - PRAGMA statements → silently skipped
    - executescript → splits on ';' and runs each statement
    - last_insert_rowid() → intercepted, returns value from last INSERT
    """

    def __init__(self, url: str, token: str):
        # Accept both libsql:// and https:// forms
        base = url.replace("libsql://", "https://").replace("wss://", "https://")
        self._url     = base.rstrip("/") + "/v2/pipeline"
        self._headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type":  "application/json",
        }
        self._last_rowid: int | None = None

    # ── row_factory compat ────────────────────────────────────────────────────
    @property
    def row_factory(self):  return None
    @row_factory.setter
    def row_factory(self, _): pass

    # ── internal HTTP call ────────────────────────────────────────────────────
    def _pipeline(self, stmts: list[dict]) -> list[dict]:
        resp = _requests.post(
            self._url,
            headers=self._headers,
            json={"requests": stmts},
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()["results"]

    # ── type coercion ─────────────────────────────────────────────────────────
    @staticmethod
    def _to_arg(val: Any) -> dict:
        if val is None:                         return {"type": "null"}
        if isinstance(val, bool):               return {"type": "integer", "value": str(int(val))}
        if isinstance(val, int):                return {"type": "integer", "value": str(val)}
        if isinstance(val, float):              return {"type": "float",   "value": val}   # must be numeric, not string
        return {"type": "text", "value": str(val)}

    @staticmethod
    def _from_val(typed: dict) -> Any:
        t = typed.get("type", "null")
        v = typed.get("value")
        if t == "null":    return None
        if t == "integer": return int(v)   if v is not None else 0
        if t == "float":   return float(v) if v is not None else 0.0
        return v   # text / blob

    # ── execute ───────────────────────────────────────────────────────────────
    def execute(self, sql: str, params=()) -> _StaticCursor | _EmptyCursor:
        stripped = sql.strip().upper()

        # Skip PRAGMAs — Turso doesn't support them
        if stripped.startswith("PRAGMA"):
            return _EmptyCursor()

        # Intercept last_insert_rowid() — return the cached value
        if "LAST_INSERT_ROWID" in stripped:
            val = self._last_rowid or 0
            return _StaticCursor(["last_insert_rowid()"],
                                  [_DictRow(["last_insert_rowid()"], [val])])

        # Named params (dict) → Turso named_args; positional (list/tuple) → args
        if isinstance(params, dict):
            stmt = {
                "sql": sql,
                "named_args": [
                    {"name": k, "value": self._to_arg(v)}
                    for k, v in params.items()
                ],
            }
        else:
            stmt = {
                "sql": sql,
                "args": [self._to_arg(p) for p in (params or [])],
            }

        results = self._pipeline([
            {"type": "execute", "stmt": stmt},
            {"type": "close"},
        ])

        res = results[0]
        if res.get("type") == "error":
            msg = res.get("error", {}).get("message", str(res))
            # Raise IntegrityError for constraint violations so callers can dedup
            if "UNIQUE constraint" in msg or "UNIQUE" in msg.upper():
                raise sqlite3.IntegrityError(msg)
            raise sqlite3.OperationalError(msg)

        result = res["response"]["result"]

        # Cache last_insert_rowid for subsequent SELECT last_insert_rowid()
        rawid = result.get("last_insert_rowid")
        if rawid is not None:
            self._last_rowid = int(rawid)

        cols = [c["name"] for c in result.get("cols", [])]
        rows = [
            _DictRow(cols, [self._from_val(cell) for cell in row])
            for row in result.get("rows", [])
        ]
        return _StaticCursor(cols, rows, self._last_rowid)

    def executemany(self, sql: str, seq) -> _EmptyCursor:
        for params in seq:
            self.execute(sql, params)
        return _EmptyCursor()

    def executescript(self, sql: str) -> _EmptyCursor:
        """sqlite3.executescript compat — splits on ';' and runs each."""
        for stmt in sql.split(";"):
            s = stmt.strip()
            if s:
                self.execute(s)
        return _EmptyCursor()

    def commit(self):
        pass   # Turso HTTP API is auto-commit per statement

    def close(self):
        pass

    def __enter__(self):  return self
    def __exit__(self, *_): self.close()


# ── Factory + first-boot seeding ─────────────────────────────────────────────

def connect() -> TursoConn:
    """Create a TursoConn from TURSO_DATABASE_URL / TURSO_AUTH_TOKEN env vars."""
    url   = os.environ["TURSO_DATABASE_URL"]
    token = os.environ.get("TURSO_AUTH_TOKEN", "")
    return TursoConn(url, token)


def seed_from_sqlite(turso: TursoConn, sqlite_path: Path) -> None:
    """
    Copy all rows from a local SQLite DB into Turso if the remote table is empty.
    Call this AFTER _create_tables so the schema already exists.
    Uses batched pipeline requests (50 rows per HTTP call) for speed.
    """
    if not sqlite_path.exists():
        print(f"[turso] seed skipped — {sqlite_path} not found")
        return

    # Check whether Turso already has data
    try:
        cur = turso.execute("SELECT COUNT(*) FROM jobs")
        row = cur.fetchone()
        if row and (row[0] or 0) > 0:
            print(f"[turso] seed skipped — remote already has {row[0]} rows")
            return
    except Exception as e:
        print(f"[turso] seed skipped — could not query remote: {e}")
        return

    try:
        src = sqlite3.connect(str(sqlite_path))
        src.row_factory = sqlite3.Row
        jobs = [dict(r) for r in src.execute("SELECT * FROM jobs").fetchall()]
        src.close()
    except Exception as e:
        print(f"[turso] seed skipped — could not read local DB: {e}")
        return

    if not jobs:
        print("[turso] seed skipped — local DB is empty")
        return

    cols = [c for c in jobs[0].keys() if c != "id"]
    placeholders = ", ".join("?" * len(cols))
    col_names    = ", ".join(cols)
    sql = f"INSERT OR IGNORE INTO jobs ({col_names}) VALUES ({placeholders})"

    # Batch 50 rows per HTTP pipeline request instead of 1 per request
    BATCH = 50
    ok = fail = 0
    for i in range(0, len(jobs), BATCH):
        batch = jobs[i : i + BATCH]
        stmts = []
        for job in batch:
            args = [turso._to_arg(job.get(c)) for c in cols]
            stmts.append({"type": "execute", "stmt": {"sql": sql, "args": args}})
        stmts.append({"type": "close"})
        try:
            results = turso._pipeline(stmts)
            for r in results:
                if r.get("type") == "error":
                    fail += 1
                elif r.get("type") == "ok":
                    ok += 1
        except Exception as e:
            fail += len(batch)
            print(f"[turso] batch {i//BATCH + 1} failed: {e}")

    print(f"[turso] seeded {ok} jobs from {sqlite_path}" + (f" ({fail} skipped/failed)" if fail else ""))
