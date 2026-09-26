"""
Causal graph models for Pipeline Autopilot.

Represents the directed acyclic graph (DAG) that explains *why* a CI/CD
pipeline failed.  The graph is produced by the Causal Chain Builder (Task 7)
and consumed by the Fix Generator (Task 8), the SSE stream (Task 9), and the
frontend Evidence Panel.

Design
------
- CausalNode    — one node in the DAG (change, dependency break, test failure, …)
- CausalEdge    — one directed edge with a typed relation and plain-language explanation
- CausalChain   — the complete DAG for one investigation, with a narrative summary

Every node carries a list of ``evidence_ids`` so that every causal claim can
be traced back to a concrete evidence artifact produced by an investigator.
No claim is allowed without evidence support.

Node types (CausalNodeType)
---------------------------
CHANGE          — a code or dependency change observed in the commit
DEPENDENCY_BREAK — a breaking API/contract change introduced by the dependency
FAILURE         — the directly observed CI failure (from FailureEvidence)
CASCADE         — a downstream effect caused by an earlier node
ROOT_CAUSE      — the singular root cause node; there is exactly one per chain
FIX             — placeholder reserved for Task 8 (Fix Generator)

Edge relations (CausalRelation)
--------------------------------
CAUSED          — node A directly caused node B
CONTRIBUTED_TO  — node A was a contributing (non-sole) factor to node B
TRIGGERED       — node A triggered the execution path that revealed node B
PROPAGATED_TO   — the effect propagated to a downstream component
"""

from __future__ import annotations

from enum import Enum
from typing import Annotated

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Bounded enumerations
# ---------------------------------------------------------------------------


class CausalNodeType(str, Enum):
    """Semantic role of a node in the causal DAG."""

    CHANGE = "CHANGE"
    DEPENDENCY_BREAK = "DEPENDENCY_BREAK"
    FAILURE = "FAILURE"
    CASCADE = "CASCADE"
    ROOT_CAUSE = "ROOT_CAUSE"
    FIX = "FIX"


class CausalRelation(str, Enum):
    """Typed relation on a causal edge."""

    CAUSED = "caused"
    CONTRIBUTED_TO = "contributed_to"
    TRIGGERED = "triggered"
    PROPAGATED_TO = "propagated_to"


# ---------------------------------------------------------------------------
# Confidence — reusable annotated type (mirrors evidence.py)
# ---------------------------------------------------------------------------

Confidence = Annotated[float, Field(ge=0.0, le=1.0)]


# ---------------------------------------------------------------------------
# CausalNode
# ---------------------------------------------------------------------------


class CausalNode(BaseModel):
    """
    One node in the causal DAG.

    Fields
    ------
    node_id:
        Stable identifier within this chain (e.g. ``"node-change-1"``).
    node_type:
        Semantic role of this node.
    label:
        Short display text (≤ 60 chars) suitable for a graph node label.
    description:
        Plain-language explanation of what happened at this node.
    evidence_ids:
        IDs of the evidence artifacts that support this node.  Must be
        non-empty for all nodes except FIX placeholders — every causal
        claim must be traceable to real evidence.
    confidence:
        Aggregate confidence for this node, derived from supporting evidence.
    """

    node_id: str = Field(description="Stable identifier for this node within the chain")
    node_type: CausalNodeType
    label: str = Field(description="Short display text for graph rendering (≤ 60 chars)")
    description: str = Field(description="Plain-language explanation of what happened at this node")
    evidence_ids: list[str] = Field(
        default_factory=list,
        description="Evidence artifact IDs that support this causal claim",
    )
    confidence: Confidence = Field(
        description="Confidence in this causal node (0.0–1.0), derived from evidence"
    )

    model_config = {"frozen": True}


# ---------------------------------------------------------------------------
# CausalEdge
# ---------------------------------------------------------------------------


class CausalEdge(BaseModel):
    """
    A directed edge in the causal DAG.

    Fields
    ------
    edge_id:
        Stable identifier for this edge within the chain.
    source_node_id:
        The causing node.
    target_node_id:
        The affected node.
    relation:
        Typed relationship between source and target.
    explanation:
        Plain-language explanation suitable for a non-technical audience.
    """

    edge_id: str = Field(description="Stable identifier for this edge")
    source_node_id: str
    target_node_id: str
    relation: CausalRelation
    explanation: str = Field(
        description="Plain-language explanation of why source caused / contributed to target"
    )

    model_config = {"frozen": True}


# ---------------------------------------------------------------------------
# CausalChain
# ---------------------------------------------------------------------------


class CausalChain(BaseModel):
    """
    The complete causal DAG for one pipeline failure investigation.

    Fields
    ------
    chain_id:
        Unique identifier for this chain (e.g. ``"chain-<pipeline_id>"``).
    pipeline_id:
        The pipeline run this chain was built for.
    nodes:
        All nodes in the DAG, in topological order (root → terminal).
    edges:
        All edges in the DAG.
    root_cause_node_id:
        The ``node_id`` of the single ROOT_CAUSE node.
    narrative:
        2–3 sentence plain-language explanation shown to a non-technical
        audience (e.g. a judge or product manager).
    confidence:
        Overall chain confidence (minimum confidence across all nodes).
    builder_version:
        Version string for the rule set used to build this chain.
        Allows reproducibility tracking.
    """

    chain_id: str
    pipeline_id: str
    nodes: list[CausalNode] = Field(default_factory=list)
    edges: list[CausalEdge] = Field(default_factory=list)
    root_cause_node_id: str
    narrative: str = Field(
        description="2–3 sentence plain-language explanation for a non-technical audience"
    )
    confidence: Confidence = Field(
        description="Overall chain confidence — minimum confidence across all nodes"
    )
    builder_version: str = Field(
        default="1.0",
        description="Version of the rule set used to build this chain",
    )

    model_config = {"frozen": True}
