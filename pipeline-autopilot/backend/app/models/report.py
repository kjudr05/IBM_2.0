"""
RecoveryReport — final report combining all investigation outputs.

Produced by the SSE stream handler once all pipeline phases complete.
Stored via set_state / get_state and served by GET /api/report/{id}.

Design (plan section 2.5)
--------------------------
RecoveryReport
    report_id:            str
    pipeline_id:          str
    created_at:           datetime
    root_cause_summary:   str     # Level 1 — one sentence
    causal_explanation:   str     # Level 2 — paragraph
    evidence_summary:     dict    # Level 3 — links to each evidence artifact
    proposed_fix:         FixProposal
    validation_result:    ValidationResult
    causal_chain:         CausalChain
    counterfactual:       dict    # serialised CounterfactualResult (dataclass)

Notes
-----
- The model is frozen — no in-place mutation after construction.
- ``counterfactual`` is stored as a plain dict because CounterfactualResult
  is a dataclass (not a Pydantic model) and contains nested dataclasses.
  The dict is a faithful serialisation of the CounterfactualResult.
- ``evidence_summary`` maps evidence_id → evidence_type for the 6 artifacts.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models.causal import CausalChain
from app.models.fix import FixProposal, ValidationResult


class RecoveryReport(BaseModel):
    """
    Final recovery report for a pipeline failure investigation.

    Produced when the complete SSE story has been played out.  Serves as
    the persistent record that GET /api/report/{id} returns.
    """

    report_id: str = Field(description="Stable identifier for this report (e.g. 'report-<pipeline_id>')")
    pipeline_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    root_cause_summary: str = Field(
        description="One-sentence root cause (Level 1 — non-technical)"
    )
    causal_explanation: str = Field(
        description="Paragraph-length causal explanation (Level 2)"
    )
    evidence_summary: dict[str, Any] = Field(
        default_factory=dict,
        description="Mapping of evidence_id → evidence metadata (Level 3)",
    )
    proposed_fix: FixProposal
    validation_result: ValidationResult
    causal_chain: CausalChain
    counterfactual: dict[str, Any] = Field(
        default_factory=dict,
        description="Serialised CounterfactualResult (before/after system snapshots)",
    )

    model_config = {"frozen": True}
