"""
Counterfactual simulator — deterministic, rule-based prediction of system
state after a proposed fix is applied.

No LLM call is made.  The simulation applies fix-type rules to the current
(broken) causal chain and predicts which nodes recover.

Design (plan section 10)
-------------------------
CounterfactualResult
    pipeline_id:    str
    fix_id:         str
    before_state:   SystemSnapshot   — all affected nodes are FAILED/DEGRADED
    after_state:    SystemSnapshot   — predicted state after fix
    changed_nodes:  list[str]        — node_ids whose health changes
    narrative:      str              — plain-language prediction

SystemSnapshot
    nodes:  dict[str, NodeHealth]    — node_id → HEALTHY | DEGRADED | FAILED

Rules
-----
DEPENDENCY_CHANGE fix:
    - Mark all DEPENDENCY_BREAK nodes HEALTHY.
    - Mark ROOT_CAUSE node HEALTHY.
    - Propagate HEALTHY to all downstream FAILURE / CASCADE nodes if their
      *only* upstream node was the now-resolved dependency break.
    - For the MVP (scenario-001) all affected nodes recover.

CODE_PATCH / CONFIG_CHANGE / ENV_FIX fix:
    - Mark the ROOT_CAUSE node HEALTHY and propagate to direct dependents.

All other nodes stay as-is.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from app.models.causal import CausalChain, CausalNodeType
from app.models.fix import FixProposal, FixType


# ---------------------------------------------------------------------------
# NodeHealth enumeration
# ---------------------------------------------------------------------------


class NodeHealth(str, Enum):
    """Health status of a node in a system snapshot."""

    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    FAILED = "FAILED"


# ---------------------------------------------------------------------------
# SystemSnapshot
# ---------------------------------------------------------------------------


@dataclass
class SystemSnapshot:
    """
    Maps each causal-chain node_id to its predicted health status.

    Attributes
    ----------
    nodes:
        Mapping of node_id → NodeHealth.
    """

    nodes: dict[str, NodeHealth] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# CounterfactualResult
# ---------------------------------------------------------------------------


@dataclass
class CounterfactualResult:
    """
    Prediction of system state before and after a fix is applied.

    Produced by :func:`simulate`.

    Attributes
    ----------
    pipeline_id:
        The pipeline run this simulation covers.
    fix_id:
        The fix proposal being evaluated.
    before_state:
        System snapshot with all failing/degraded nodes as observed.
    after_state:
        System snapshot with predicted state after the fix is applied.
    changed_nodes:
        node_ids whose health status changes between before and after.
    narrative:
        2–3 sentence plain-language prediction suitable for a non-technical
        audience.
    """

    pipeline_id: str
    fix_id: str
    before_state: SystemSnapshot
    after_state: SystemSnapshot
    changed_nodes: list[str]
    narrative: str


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def simulate(chain: CausalChain, fix: FixProposal) -> CounterfactualResult:
    """
    Predict system state after ``fix`` is applied to the pipeline described
    by ``chain``.

    Parameters
    ----------
    chain:
        The causal chain produced for this pipeline failure.
    fix:
        The proposed fix to evaluate.

    Returns
    -------
    CounterfactualResult
        Deterministic prediction — identical inputs always produce identical
        output.
    """
    before = _build_before_snapshot(chain)
    after, changed = _apply_fix_rules(chain, fix, before)
    narrative = _build_narrative(fix, changed, chain)

    return CounterfactualResult(
        pipeline_id=chain.pipeline_id,
        fix_id=fix.fix_id,
        before_state=before,
        after_state=after,
        changed_nodes=changed,
        narrative=narrative,
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _build_before_snapshot(chain: CausalChain) -> SystemSnapshot:
    """
    Build the 'before' snapshot: assign health based on node type.

    ROOT_CAUSE, DEPENDENCY_BREAK → FAILED
    FAILURE, CASCADE             → FAILED
    CHANGE                       → DEGRADED  (change observed but not itself broken)
    FIX                          → HEALTHY   (placeholder — not yet applied)
    """
    _TYPE_TO_HEALTH: dict[CausalNodeType, NodeHealth] = {
        CausalNodeType.CHANGE: NodeHealth.DEGRADED,
        CausalNodeType.DEPENDENCY_BREAK: NodeHealth.FAILED,
        CausalNodeType.FAILURE: NodeHealth.FAILED,
        CausalNodeType.CASCADE: NodeHealth.FAILED,
        CausalNodeType.ROOT_CAUSE: NodeHealth.FAILED,
        CausalNodeType.FIX: NodeHealth.HEALTHY,
    }
    return SystemSnapshot(
        nodes={
            node.node_id: _TYPE_TO_HEALTH.get(node.node_type, NodeHealth.DEGRADED)
            for node in chain.nodes
        }
    )


def _apply_fix_rules(
    chain: CausalChain,
    fix: FixProposal,
    before: SystemSnapshot,
) -> tuple[SystemSnapshot, list[str]]:
    """
    Apply fix-type rules and return (after_snapshot, changed_node_ids).

    Rules (priority order)
    ----------------------
    DEPENDENCY_CHANGE fix:
        All DEPENDENCY_BREAK, ROOT_CAUSE, FAILURE, and CASCADE nodes recover
        (mark HEALTHY) because the dependency pin removes the root cause.

    CODE_PATCH / CONFIG_CHANGE / ENV_FIX fix:
        ROOT_CAUSE and all downstream FAILURE / CASCADE nodes recover.

    All other nodes retain their before-state health.
    """
    import copy

    after_nodes: dict[str, NodeHealth] = copy.copy(before.nodes)
    changed: list[str] = []

    if fix.fix_type == FixType.DEPENDENCY_CHANGE:
        # A dependency pin resolves the breaking change entirely — all
        # failing/degraded nodes caused by the dep upgrade recover.
        recovery_types = {
            CausalNodeType.DEPENDENCY_BREAK,
            CausalNodeType.ROOT_CAUSE,
            CausalNodeType.FAILURE,
            CausalNodeType.CASCADE,
        }
        for node in chain.nodes:
            if node.node_type in recovery_types:
                if after_nodes.get(node.node_id) != NodeHealth.HEALTHY:
                    after_nodes[node.node_id] = NodeHealth.HEALTHY
                    changed.append(node.node_id)

    else:
        # CODE_PATCH / CONFIG_CHANGE / ENV_FIX — recover root cause + failures
        recovery_types = {
            CausalNodeType.ROOT_CAUSE,
            CausalNodeType.FAILURE,
            CausalNodeType.CASCADE,
        }
        for node in chain.nodes:
            if node.node_type in recovery_types:
                if after_nodes.get(node.node_id) != NodeHealth.HEALTHY:
                    after_nodes[node.node_id] = NodeHealth.HEALTHY
                    changed.append(node.node_id)

    return SystemSnapshot(nodes=after_nodes), changed


def _build_narrative(
    fix: FixProposal,
    changed_nodes: list[str],
    chain: CausalChain,
) -> str:
    """Build a plain-language narrative for the counterfactual prediction."""
    n = len(changed_nodes)
    node_word = "node" if n == 1 else "nodes"

    if fix.fix_type == FixType.DEPENDENCY_CHANGE:
        dep_changes = fix.dependency_changes
        if dep_changes:
            dep = dep_changes[0]
            return (
                f"If {dep.name} is pinned back from {dep.old_version} to "
                f"{dep.new_version}, the breaking API change is removed. "
                f"The {n} affected {node_word} in the causal chain will "
                f"transition from FAILED to HEALTHY. "
                f"Pipeline tests are expected to pass again."
            )

    # Fallback narrative
    return (
        f"Applying the proposed fix is predicted to resolve {n} failing "
        f"{node_word} in the causal chain. "
        f"The pipeline is expected to recover to a healthy state."
    )
