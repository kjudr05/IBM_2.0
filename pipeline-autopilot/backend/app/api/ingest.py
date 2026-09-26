"""
POST /api/ingest — receive a raw PipelineFailureEvent JSON body and store it.

The response envelope follows the project convention:
    { "data": {...}, "error": null }
or on failure:
    { "data": null, "error": "message" }

This router handles only the raw ingest path.
The /api/scenarios/{id}/load path (sample-data loader) lives in scenarios.py.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.db.store import save_pipeline
from app.models.events import PipelineFailureEvent

router = APIRouter(tags=["ingest"])


@router.post("/ingest", status_code=status.HTTP_201_CREATED)
async def ingest_event(event: PipelineFailureEvent) -> dict:
    """
    Accept a PipelineFailureEvent and persist it to SQLite.

    Returns the pipeline id so the caller can open the SSE stream.
    """
    try:
        pipeline_id = await save_pipeline(event)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    return {"data": {"pipeline_id": pipeline_id}, "error": None}
