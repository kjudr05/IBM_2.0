"""
GET /api/report/{id} — return the final RecoveryReport JSON.

The report is written to pipeline_state by the SSE stream handler once
the full pipeline completes.  This endpoint reads it back and returns it.

Response envelope: { "data": {...}, "error": null }
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.db.store import get_pipeline, get_state
from app.models.report import RecoveryReport

router = APIRouter(tags=["report"])


@router.get("/report/{pipeline_id}")
async def get_report(pipeline_id: str) -> dict:
    """
    Return the final RecoveryReport for a completed pipeline run.

    Returns 404 if the pipeline does not exist.
    Returns 202 (Accepted) if the pipeline has not yet completed.
    """
    record = await get_pipeline(pipeline_id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pipeline '{pipeline_id}' not found",
        )

    report_json = await get_state(pipeline_id, "report")
    if report_json is None:
        pipeline_status = await get_state(pipeline_id, "status") or "pending"
        raise HTTPException(
            status_code=status.HTTP_202_ACCEPTED,
            detail=f"Report not yet available (pipeline status: {pipeline_status})",
        )

    report = RecoveryReport.model_validate_json(report_json)
    return {"data": report.model_dump(mode="json"), "error": None}
