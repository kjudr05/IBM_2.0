"""
InvestigationResult — the output of the Orchestrator.

Produced after all six investigators have run (or attempted to run).
Carries:

- scenario / pipeline identity
- all successfully collected evidence artifacts
- per-investigator status (success or error)
- overall investigation status
- wall-clock timing

This model is the *input* to the Causal Chain Builder (Task 7).  It must
contain everything the builder needs and nothing specific to the UI layer.

Design notes
------------
- ``status`` is ``COMPLETE`` if every investigator succeeded.
- ``status`` is ``PARTIAL`` if at least one succeeded and at least one failed.
- ``status`` is ``FAILED`` if every investigator raised an exception
  (or the orchestrator itself could not proceed).
- ``errors`` maps agent_id → error message for every investigator that failed.
- ``evidence`` preserves all successfully collected artifacts; failed
  investigators simply have no artifact in this list.
- The model is intentionally NOT frozen: orchestrator builds it incrementally.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from app.models.evidence import BaseEvidence


# ---------------------------------------------------------------------------
# Status enumeration
# ---------------------------------------------------------------------------


class InvestigationStatus(str, Enum):
    """Overall outcome of an investigation run."""

    COMPLETE = "complete"   # all investigators succeeded
    PARTIAL = "partial"     # some succeeded, some failed
    FAILED = "failed"       # all investigators failed (or setup error)


# ---------------------------------------------------------------------------
# Per-investigator outcome record
# ---------------------------------------------------------------------------


class InvestigatorOutcome(BaseModel):
    """
    Records the outcome for one investigator within a run.

    Used by the orchestrator to communicate which agents produced evidence
    and which raised errors.
    """

    agent_id: str = Field(description="Investigator that produced this outcome")
    success: bool
    evidence_id: str | None = Field(
        default=None,
        description="evidence_id of the artifact published on success, None on failure",
    )
    error: str | None = Field(
        default=None,
        description="Error message if the investigator failed, None on success",
    )

    model_config = {"frozen": True}


# ---------------------------------------------------------------------------
# InvestigationResult
# ---------------------------------------------------------------------------


class InvestigationResult(BaseModel):
    """
    Output of the Orchestrator — input to the Causal Chain Builder.

    Fields
    ------
    pipeline_id:
        The ``pipeline_run_id`` from the originating :class:`PipelineFailureEvent`.
    scenario_id:
        Scenario used for this investigation (e.g. ``"scenario-001"``).
    status:
        Overall investigation status (COMPLETE / PARTIAL / FAILED).
    evidence:
        All successfully collected evidence artifacts, sorted by ``created_at``.
    outcomes:
        Per-investigator success/failure record (one entry per investigator).
    errors:
        Mapping of ``agent_id`` → error message for every investigator that
        raised an exception.  Empty dict when all investigators succeed.
    started_at:
        UTC timestamp when the orchestrator began dispatching investigators.
    completed_at:
        UTC timestamp when the orchestrator finished collecting all results.
    metadata:
        Open dict for orchestrator-specific extras (kept small).
    """

    pipeline_id: str
    scenario_id: str
    status: InvestigationStatus
    evidence: list[BaseEvidence] = Field(default_factory=list)
    outcomes: list[InvestigatorOutcome] = Field(default_factory=list)
    errors: dict[str, str] = Field(
        default_factory=dict,
        description="agent_id → error message for each failed investigator",
    )
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
