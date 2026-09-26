"""
SQLite database connection and schema initialisation for Pipeline Autopilot.

The database file is created at the path configured by the DATA_DIR environment
variable (default: ./data/pipeline_autopilot.db).  The data/ directory is
git-ignored and created at startup.

Schema (Task 3 — minimal for ingest):
    pipelines       — one row per ingested PipelineFailureEvent
    pipeline_state  — key/value store for mutable pipeline processing state
                      (used by Tasks 6+ when the orchestrator updates status)

Both tables are created with CREATE TABLE IF NOT EXISTS so the app can restart
safely without re-running migrations.
"""

from __future__ import annotations

import asyncio
import os
import pathlib

import aiosqlite

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_DEFAULT_DATA_DIR = pathlib.Path(__file__).parent.parent.parent.parent / "data"


def _db_path() -> pathlib.Path:
    data_dir = pathlib.Path(os.environ.get("DATA_DIR", str(_DEFAULT_DATA_DIR)))
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / "pipeline_autopilot.db"


# ---------------------------------------------------------------------------
# DDL
# ---------------------------------------------------------------------------

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS pipelines (
    id              TEXT PRIMARY KEY,
    repo            TEXT NOT NULL,
    branch          TEXT NOT NULL,
    commit_sha      TEXT NOT NULL,
    pipeline_run_id TEXT NOT NULL,
    failure_stage   TEXT NOT NULL,
    created_at      TEXT NOT NULL,
    event_json      TEXT NOT NULL    -- full PipelineFailureEvent serialised as JSON
);

CREATE TABLE IF NOT EXISTS pipeline_state (
    pipeline_id     TEXT NOT NULL,
    key             TEXT NOT NULL,
    value           TEXT NOT NULL,
    updated_at      TEXT NOT NULL,
    PRIMARY KEY (pipeline_id, key),
    FOREIGN KEY (pipeline_id) REFERENCES pipelines(id)
);

CREATE INDEX IF NOT EXISTS idx_pipeline_state_pipeline_id
    ON pipeline_state (pipeline_id);
"""

# ---------------------------------------------------------------------------
# Connection lifecycle
# ---------------------------------------------------------------------------

_connection: aiosqlite.Connection | None = None
_lock = asyncio.Lock()


async def get_db() -> aiosqlite.Connection:
    """Return the shared database connection, opening it if necessary."""
    global _connection
    async with _lock:
        if _connection is None:
            _connection = await aiosqlite.connect(str(_db_path()))
            _connection.row_factory = aiosqlite.Row
            await _connection.execute("PRAGMA journal_mode=WAL")
            await _connection.execute("PRAGMA foreign_keys=ON")
        return _connection


async def init_db() -> None:
    """Create tables if they don't exist.  Safe to call on every startup."""
    db = await get_db()
    await db.executescript(_SCHEMA_SQL)
    await db.commit()


async def close_db() -> None:
    """Close the shared connection.  Called from FastAPI lifespan shutdown."""
    global _connection
    async with _lock:
        if _connection is not None:
            await _connection.close()
            _connection = None
