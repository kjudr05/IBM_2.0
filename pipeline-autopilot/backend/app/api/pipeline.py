"""
GET /api/pipeline/{id} — return the full pipeline state snapshot.

Returns the stored PipelineFailureEvent plus any key/value state entries
written by the orchestrator (Tasks 6+).

Response envelope: { "data": {...}, "error": null }
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.db.store import get_pipeline, get_state

router = APIRouter(tags=["pipeline"])


@router.get("/pipeline/{pipeline_id}")
async def get_pipeline_state(pipeline_id: str) -> dict:
    """Return the stored event and current processing state for a pipeline."""
    record = await get_pipeline(pipeline_id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pipeline '{pipeline_id}' not found",
        )

    # Read the mutable processing state written by the orchestrator.
    # At Task 3 this will always be None; populated in Tasks 6+.
    processing_status = await get_state(pipeline_id, "status")

    return {
        "data": {
            "pipeline_id": record.id,
            "repo": record.repo,
            "branch": record.branch,
            "commit_sha": record.commit_sha,
            "pipeline_run_id": record.pipeline_run_id,
            "failure_stage": record.failure_stage,
            "created_at": record.created_at,
            "status": processing_status or "pending",
            "event": record.event.model_dump(),
        },
        "error": None,
    }
