"""
Turso / libsql adapter — makes a libsql connection look like sqlite3.Connection
so tracker.py works unmodified.

Used automatically by api/main.py when TURSO_DATABASE_URL is set.
"""

from __future__ import annotations
import os


class _EmptyCursor:
    """Returned for PRAGMA statements that Turso doesn't support."""
    description = None
    lastrowid   = None

    def fetchone(self):  return None
    def fetchall(self):  return []


class _DictRow:
    """
    Dict- and index-accessible row, mimics sqlite3.Row.
    Supports row["col"], row[0], row.get("col"), row.keys(), iter(row).
    """
    __slots__ = ("_d", "_v")

    def __init__(self, keys: list[str], values):
        self._v = list(values)
        self._d = dict(zip(keys, values))

    def __getitem__(self, key):
        if isinstance(key, int):
            return self._v[key]
        return self._d[key]

    def get(self, key, default=None):
        return self._d.get(key, default)

    def keys(self):
        return self._d.keys()

    def __iter__(self):
        return iter(self._v)

    def __repr__(self):
        return repr(self._d)


class _Cursor:
    """Wraps a libsql cursor; fetchone / fetchall return _DictRow objects."""

    def __init__(self, cursor):
        self._c = cursor
        self._keys: list[str] | None = None

    def _resolve_keys(self):
        if self._keys is None and self._c.description:
            self._keys = [d[0] for d in self._c.description]
        return self._keys or []

    def fetchone(self):
        row = self._c.fetchone()
        return None if row is None else _DictRow(self._resolve_keys(), row)

    def fetchall(self):
        rows = self._c.fetchall()
        keys = self._resolve_keys()
        return [_DictRow(keys, r) for r in rows]

    @property
    def description(self):
        return self._c.description

    @property
    def lastrowid(self):
        return getattr(self._c, "lastrowid", None)


_PRAGMA_PREFIXES = ("PRAGMA",)


class TursoConn:
    """
    sqlite3.Connection-compatible wrapper for a libsql connection.

    Key differences handled transparently:
    - row_factory setter → no-op (rows handled by _Cursor / _DictRow)
    - PRAGMA statements → silently skipped (not supported by Turso)
    - commit() → also syncs to the remote Turso database
    """

    def __init__(self, conn):
        self._conn = conn

    # ── row_factory compatibility ─────────────────────────────────────────────
    @property
    def row_factory(self):
        return None

    @row_factory.setter
    def row_factory(self, _):
        pass   # sqlite3.Row assignment — ignored, _Cursor handles this

    # ── execute ───────────────────────────────────────────────────────────────
    def execute(self, sql: str, params=()):
        stripped = sql.strip().upper()
        if any(stripped.startswith(p) for p in _PRAGMA_PREFIXES):
            return _EmptyCursor()
        return _Cursor(self._conn.execute(sql, params))

    def executemany(self, sql: str, seq):
        stripped = sql.strip().upper()
        if any(stripped.startswith(p) for p in _PRAGMA_PREFIXES):
            return _EmptyCursor()
        return self._conn.executemany(sql, seq)

    def executescript(self, sql: str):
        """sqlite3.executescript compat — splits on ';' and runs each statement."""
        for stmt in sql.split(";"):
            stmt = stmt.strip()
            if stmt:
                self.execute(stmt)
        self.commit()
        return _EmptyCursor()

    # ── commit / sync ─────────────────────────────────────────────────────────
    def commit(self):
        self._conn.commit()
        # libsql embedded-replica: push local writes to Turso
        if hasattr(self._conn, "sync"):
            self._conn.sync()

    # ── misc ──────────────────────────────────────────────────────────────────
    def close(self):
        self._conn.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()


def connect(db_path: str) -> TursoConn:
    """
    Build a TursoConn.

    In production (TURSO_DATABASE_URL set):
      - Creates an embedded replica synced to Turso.
      - Local writes are durable on disk AND replicated to the cloud.
      - db_path is used as the local replica file path.

    Locally (TURSO_DATABASE_URL not set):
      - Falls through to a plain sqlite3 connection (see api/main.py).
    """
    try:
        import libsql_experimental as libsql
    except ImportError as e:
        raise RuntimeError(
            "libsql-experimental is not installed. "
            "Run: pip install libsql-experimental"
        ) from e

    url   = os.environ["TURSO_DATABASE_URL"]
    token = os.environ.get("TURSO_AUTH_TOKEN", "")

    # Embedded replica: keeps a local SQLite file, syncs with Turso
    conn = libsql.connect(
        database=str(db_path),
        sync_url=url,
        auth_token=token,
    )
    conn.sync()   # pull latest from remote on startup
    return TursoConn(conn)
