Here's a focused example covering connection lifecycle and context manager patterns for a SQLite-backed app in Python 3.14+.

```python
import sqlite3
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path("app.db")


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

DDL = """
CREATE TABLE IF NOT EXISTS notes (
    id    INTEGER PRIMARY KEY,
    title TEXT    NOT NULL,
    body  TEXT    NOT NULL DEFAULT ''
);
"""


# ---------------------------------------------------------------------------
# Connection lifecycle
# ---------------------------------------------------------------------------

def open_db(path: Path = DB_PATH) -> sqlite3.Connection:
    """
    Open (or create) the database and configure it for the session.
    Call once at app startup; hold the connection for the lifetime of the app.
    """
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row   # rows behave like dicts
    conn.execute("PRAGMA journal_mode=WAL")   # better concurrency
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(DDL)
    return conn


def close_db(conn: sqlite3.Connection) -> None:
    """Call once at app shutdown."""
    conn.close()


# ---------------------------------------------------------------------------
# Context manager for transactions
# ---------------------------------------------------------------------------

@contextmanager
def transaction(conn: sqlite3.Connection):
    """
    Wrap a block in an explicit transaction.
    Commits on clean exit, rolls back on any exception.

    sqlite3.connect() has autocommit behaviour that changed in 3.12 and was
    further clarified in 3.14 (PEP 249-compliant isolation_level=None gives
    you a pure manual-commit mode). Using an explicit context manager here
    keeps intent clear regardless of the default.
    """
    try:
        conn.execute("BEGIN")
        yield conn
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise


# ---------------------------------------------------------------------------
# Data access
# ---------------------------------------------------------------------------

def add_note(conn: sqlite3.Connection, title: str, body: str = "") -> int:
    with transaction(conn) as c:
        cur = c.execute(
            "INSERT INTO notes (title, body) VALUES (?, ?)", (title, body)
        )
        return cur.lastrowid


def get_note(conn: sqlite3.Connection, note_id: int) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM notes WHERE id = ?", (note_id,)
    ).fetchone()


def list_notes(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute("SELECT * FROM notes ORDER BY id").fetchall()


def delete_note(conn: sqlite3.Connection, note_id: int) -> bool:
    with transaction(conn) as c:
        cur = c.execute("DELETE FROM notes WHERE id = ?", (note_id,))
        return cur.rowcount > 0


# ---------------------------------------------------------------------------
# App entry point — connection opened once, closed once
# ---------------------------------------------------------------------------

def main() -> None:
    conn = open_db()
    try:
        # normal app work
        id1 = add_note(conn, "Shopping list", "Milk, eggs, bread")
        id2 = add_note(conn, "Ideas", "Learn more SQLite pragmas")

        for row in list_notes(conn):
            print(dict(row))

        delete_note(conn, id1)
        print(f"After delete: {[dict(r) for r in list_notes(conn)]}")

    finally:
        close_db(conn)   # always runs, even if an exception escapes


if __name__ == "__main__":
    main()
```

---

### The key ideas

**One connection per process, opened at startup.**
SQLite is an in-process library; creating a connection is cheap but you don't want to open/close one per query. Open it in `main()` (or your app's init), pass it down through your call stack (or store it in an app-level object), and close it in a `finally` block at shutdown.

**Separate connection lifecycle from transaction lifecycle.**
The `transaction()` context manager controls *when work is committed or rolled back*, not when the connection lives. You can (and should) run many transactions over the same open connection.

**Why the explicit `BEGIN` / `COMMIT` / `ROLLBACK`?**
Python's `sqlite3` module has had shifting defaults around autocommit across 3.10–3.14. Writing explicit `BEGIN`/`COMMIT` removes ambiguity and works identically across versions. In 3.14+ you can also pass `autocommit=False` to `sqlite3.connect()` for strict PEP 249 behavior, but the explicit context manager pattern above is portable and obvious.

**`row_factory = sqlite3.Row`**
Makes every fetched row accessible as both `row["column"]` and `row[0]`, with no extra dependencies.

**WAL mode**
Set once at connection open time. Allows concurrent readers while a writer is active — almost always the right choice for an app database.