"""
Pipeline state store — read/write pipeline records to SQLite.

Provides a thin async repository layer over the pipelines and pipeline_state
tables.  All callers go through this module; no raw SQL elsewhere in the app.

Public API (Task 3):
    save_pipeline(event)           → str  (pipeline id)
    get_pipeline(pipeline_id)      → PipelineRecord | None
    list_pipelines()               → list[PipelineRecord]
    set_state(pipeline_id, key, value)
    get_state(pipeline_id, key)    → str | None

PipelineRecord is a lightweight dataclass; it is NOT a Pydantic model because
it carries SQLite-level metadata (created_at as plain ISO string) in addition
to the domain event.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from app.db.database import get_db
from app.models.events import PipelineFailureEvent


# ---------------------------------------------------------------------------
# Data container
# ---------------------------------------------------------------------------


@dataclass
class PipelineRecord:
    """Row returned from the pipelines table, with the event re-hydrated."""

    id: str
    repo: str
    branch: str
    commit_sha: str
    pipeline_run_id: str
    failure_stage: str
    created_at: str          # ISO-8601 string as stored in SQLite
    event: PipelineFailureEvent


# ---------------------------------------------------------------------------
# Write operations
# ---------------------------------------------------------------------------


async def save_pipeline(event: PipelineFailureEvent) -> str:
    """
    Persist a PipelineFailureEvent.

    Returns the pipeline id (same as event.id).
    Raises ValueError if a pipeline with the same id already exists.
    """
    db = await get_db()
    created_at = datetime.now(timezone.utc).isoformat()
    event_json = event.model_dump_json()

    async with db.execute(
        "SELECT id FROM pipelines WHERE id = ?", (event.id,)
    ) as cursor:
        if await cursor.fetchone() is not None:
            raise ValueError(f"Pipeline with id '{event.id}' already exists")

    await db.execute(
        """
        INSERT INTO pipelines
            (id, repo, branch, commit_sha, pipeline_run_id,
             failure_stage, created_at, event_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            event.id,
            event.repo,
            event.branch,
            event.commit_sha,
            event.pipeline_run_id,
            event.failure_stage,
            created_at,
            event_json,
        ),
    )
    await db.commit()
    return event.id


async def set_state(pipeline_id: str, key: str, value: str) -> None:
    """Upsert a key/value pair in pipeline_state for the given pipeline."""
    db = await get_db()
    updated_at = datetime.now(timezone.utc).isoformat()
    await db.execute(
        """
        INSERT INTO pipeline_state (pipeline_id, key, value, updated_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(pipeline_id, key) DO UPDATE SET
            value      = excluded.value,
            updated_at = excluded.updated_at
        """,
        (pipeline_id, key, value, updated_at),
    )
    await db.commit()


# ---------------------------------------------------------------------------
# Read operations
# ---------------------------------------------------------------------------


async def get_pipeline(pipeline_id: str) -> PipelineRecord | None:
    """Return a PipelineRecord or None if the id is not found."""
    db = await get_db()
    async with db.execute(
        "SELECT * FROM pipelines WHERE id = ?", (pipeline_id,)
    ) as cursor:
        row = await cursor.fetchone()

    if row is None:
        return None

    return _row_to_record(row)


async def list_pipelines() -> list[PipelineRecord]:
    """Return all stored pipelines, newest first."""
    db = await get_db()
    async with db.execute(
        "SELECT * FROM pipelines ORDER BY created_at DESC"
    ) as cursor:
        rows = await cursor.fetchall()

    return [_row_to_record(r) for r in rows]


async def get_state(pipeline_id: str, key: str) -> str | None:
    """Return a state value or None if the key has not been set."""
    db = await get_db()
    async with db.execute(
        "SELECT value FROM pipeline_state WHERE pipeline_id = ? AND key = ?",
        (pipeline_id, key),
    ) as cursor:
        row = await cursor.fetchone()

    return row["value"] if row is not None else None


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _row_to_record(row: object) -> PipelineRecord:
    import json

    data = dict(row)  # aiosqlite.Row supports dict()
    event = PipelineFailureEvent.model_validate_json(data["event_json"])
    return PipelineRecord(
        id=data["id"],
        repo=data["repo"],
        branch=data["branch"],
        commit_sha=data["commit_sha"],
        pipeline_run_id=data["pipeline_run_id"],
        failure_stage=data["failure_stage"],
        created_at=data["created_at"],
        event=event,
    )
