"""
Fix and validation models for Pipeline Autopilot.

ProposedFix  — a single typed fix proposal produced by the Fix Generator.
ValidationResult — the outcome of applying a fix in a sandbox (Task 9+).

Design
------
- ProposedFix is the output of ``FixGenerator.generate(chain)``.
- It carries full evidence provenance: ``root_cause_node_id`` links back to
  the CausalChain, and ``evidence_ids`` lists every evidence artifact that
  supports the fix proposal.
- ``dependency_changes`` reuses ``DepChange`` from the evidence models — no
  duplicate model.
- ``confidence`` is taken directly from the CausalChain's root-cause node so
  the fix confidence is traceable to the evidence confidence.
- The model is frozen (immutable) — no in-place mutation after construction.

FixType enumeration
-------------------
DEPENDENCY_CHANGE  — pin, downgrade, or upgrade a dependency
CODE_PATCH         — apply a source-code patch (unified diff)
CONFIG_CHANGE      — modify a CI / environment configuration value
ENV_FIX            — fix an environment variable or secret

ValidationResult is defined as a placeholder for Task 9 (SSE + validation
loop).  Its presence here lets the rest of the codebase import it without
a stub file but its fields are intentionally minimal until Task 9 implements
the validator.
"""

from __future__ import annotations

from enum import Enum
from typing import Annotated

from pydantic import BaseModel, Field

from app.models.evidence import DepChange

# ---------------------------------------------------------------------------
# FixType enumeration
# ---------------------------------------------------------------------------


class FixType(str, Enum):
    """Discriminator for the kind of fix being proposed."""

    DEPENDENCY_CHANGE = "DEPENDENCY_CHANGE"
    CODE_PATCH = "CODE_PATCH"
    CONFIG_CHANGE = "CONFIG_CHANGE"
    ENV_FIX = "ENV_FIX"


# ---------------------------------------------------------------------------
# Confidence — reusable annotated type (mirrors evidence.py / causal.py)
# ---------------------------------------------------------------------------

Confidence = Annotated[float, Field(ge=0.0, le=1.0)]


# ---------------------------------------------------------------------------
# ProposedFix
# ---------------------------------------------------------------------------


class FixProposal(BaseModel):
    """
    A proposed fix for a pipeline failure, produced by the Fix Generator.

    Fields
    ------
    fix_id:
        Stable identifier for this fix (e.g. ``"fix-<pipeline_id>"``).
    pipeline_id:
        The pipeline run this fix targets.
    root_cause_node_id:
        The ``node_id`` of the ROOT_CAUSE node in the CausalChain that this
        fix addresses.  Enables the frontend to highlight the relevant node.
    fix_type:
        Category of fix being proposed.
    description:
        Plain-language description of what the fix does
        (shown to a non-technical audience).
    rationale:
        Why this fix addresses the root cause — explicitly links fix action
        to the causal evidence.
    affected_file:
        The file or configuration that needs to be changed, when identifiable
        from the evidence (e.g. ``"package.json"``).  ``None`` when the fix
        is not tied to a specific file.
    dependency_changes:
        List of dependency version changes that form the fix.  Populated for
        ``DEPENDENCY_CHANGE`` fixes; empty for other fix types.
    patch:
        Unified diff string for ``CODE_PATCH`` fixes.  ``None`` for other
        fix types.
    config_changes:
        Key/value pairs for ``CONFIG_CHANGE`` fixes.  ``None`` for other
        fix types.
    evidence_ids:
        IDs of all evidence artifacts that support this fix proposal.
        Preserves full provenance from the CausalChain root-cause node.
    confidence:
        Fix confidence derived from the root-cause node confidence.
        Inherits the chain's evidence quality directly.
    generator_version:
        Version of the fix-generator rule set.  Allows reproducibility
        tracking across rule-set updates.
    """

    fix_id: str = Field(description="Stable identifier for this fix proposal")
    pipeline_id: str
    root_cause_node_id: str = Field(
        description="node_id of the ROOT_CAUSE node in the originating CausalChain"
    )
    fix_type: FixType
    description: str = Field(description="Plain-language description of the fix action")
    rationale: str = Field(
        description="Why this fix addresses the root cause (evidence-backed)"
    )
    affected_file: str | None = Field(
        default=None,
        description="File or configuration that needs to be changed, if identifiable",
    )
    dependency_changes: list[DepChange] = Field(
        default_factory=list,
        description="Dependency version changes that form the fix (DEPENDENCY_CHANGE only)",
    )
    patch: str | None = Field(
        default=None,
        description="Unified diff for CODE_PATCH fixes",
    )
    config_changes: dict[str, str] | None = Field(
        default=None,
        description="Key/value config changes for CONFIG_CHANGE fixes",
    )
    evidence_ids: list[str] = Field(
        default_factory=list,
        description="Evidence artifact IDs that support this fix proposal",
    )
    confidence: Confidence = Field(
        description="Fix confidence derived from the root-cause node confidence (0.0–1.0)"
    )
    generator_version: str = Field(
        default="1.0",
        description="Version of the fix-generator rule set",
    )

    model_config = {"frozen": True}


# ---------------------------------------------------------------------------
# ValidationResult — placeholder for Task 9
# ---------------------------------------------------------------------------


class ValidationStatus(str, Enum):
    """Outcome of a fix validation run."""

    PASSED = "PASSED"
    FAILED = "FAILED"
    PARTIAL = "PARTIAL"


class ValidationResult(BaseModel):
    """
    Outcome of applying a proposed fix in a simulated environment.

    Populated by Task 9 (SSE + fix-validation loop).  Defined here so that
    the rest of the codebase can import it without a stub.
    """

    validation_id: str
    fix_id: str
    status: ValidationStatus
    confidence: Confidence
    validation_narrative: str

    model_config = {"frozen": True}
