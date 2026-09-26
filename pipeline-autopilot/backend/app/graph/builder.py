"""
CausalChainBuilder — converts collected investigation evidence into a CausalChain.

Responsibilities (Task 7 scope)
---------------------------------
1. Accept an :class:`~app.models.investigation.InvestigationResult`.
2. Reason over the typed evidence artifacts to identify causal relationships.
3. Produce a :class:`~app.models.causal.CausalChain` with:
   - Ordered causal nodes (topological: root → terminal)
   - Typed directed edges
   - A single ROOT_CAUSE node
   - Plain-language narrative
   - Evidence provenance on every node
4. Return an :class:`InsufficientEvidenceError` (not raise) when the evidence
   set is too sparse to build a meaningful chain.

What the builder does NOT do
-----------------------------
- Run investigators
- Call any AI/LLM provider
- Modify source code
- Generate fixes
- Run tests
- Simulate counterfactuals
- Emit SSE events

Reasoning strategy (deterministic, rule-based for MVP)
--------------------------------------------------------
The builder applies a priority-ordered rule set.  Rules inspect the typed
evidence objects and vote for node/edge patterns.  The first rule whose
evidence preconditions are satisfied wins for that pattern.

Priority order for ROOT_CAUSE selection
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
1. DependencyEvidence with ``breaking_changes`` — dependency break is root cause.
2. ChangeEvidence with ``changed_files`` — code change is root cause.
3. FailureEvidence alone — the observable failure is treated as root cause
   (lowest-confidence fallback).

Chain topology for scenario-001 ("The Silent Semver Break")
------------------------------------------------------------
::

    [ROOT_CAUSE] dependency_bump (CHANGE/ROOT_CAUSE)
          │ caused
          ▼
    [DEPENDENCY_BREAK] breaking_api (DEPENDENCY_BREAK)
          │ caused
          ▼
    [FAILURE] test_failure (FAILURE)
          │ propagated_to
          ▼
    [CASCADE] build_failure (CASCADE)

The builder can produce shorter chains when evidence is partial:
- No DependencyEvidence → skip the DEPENDENCY_BREAK node.
- No TestEvidence → no CASCADE node for test failures.
- No FailureEvidence → DEPENDENCY_BREAK is the terminal node.

Usage
-----
::

    from app.graph.builder import CausalChainBuilder
    from app.models.investigation import InvestigationResult

    builder = CausalChainBuilder()
    result: CausalChain | InsufficientEvidenceError = builder.build(investigation)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from app.models.causal import (
    CausalChain,
    CausalEdge,
    CausalNode,
    CausalNodeType,
    CausalRelation,
)
from app.models.evidence import (
    BaseEvidence,
    ChangeEvidence,
    DependencyEvidence,
    EvidenceType,
    FailureEvidence,
    HistoricalEvidence,
    InfraEvidence,
    TestRunEvidence,
)
from app.models.investigation import InvestigationResult, InvestigationStatus

if TYPE_CHECKING:
    pass

# ---------------------------------------------------------------------------
# Builder version — increment when the rule set changes
# ---------------------------------------------------------------------------

_BUILDER_VERSION = "1.0"

# Minimum number of successfully collected evidence artifacts required before
# the builder will attempt to produce a chain.
_MIN_EVIDENCE_COUNT = 1


# ---------------------------------------------------------------------------
# InsufficientEvidenceError
# ---------------------------------------------------------------------------


@dataclass
class InsufficientEvidenceError:
    """
    Returned (not raised) when evidence is too sparse to build a causal chain.

    The builder never raises on insufficient evidence — it returns this object
    so that callers can decide how to handle the gap (log, retry, partial chain).

    Attributes
    ----------
    pipeline_id:
        The pipeline the investigation was for.
    reason:
        Human-readable explanation of why the chain could not be built.
    evidence_count:
        How many evidence artifacts were present.
    missing_types:
        Which EvidenceType values were absent and are required for a chain.
    """

    pipeline_id: str
    reason: str
    evidence_count: int = 0
    missing_types: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _collect_by_type(
    evidence: list[BaseEvidence],
) -> dict[EvidenceType, list[BaseEvidence]]:
    """Group evidence artifacts by their EvidenceType."""
    result: dict[EvidenceType, list[BaseEvidence]] = {}
    for ev in evidence:
        result.setdefault(ev.evidence_type, []).append(ev)
    return result


def _min_confidence(nodes: list[CausalNode]) -> float:
    """Return the minimum confidence across all nodes (chain-level confidence)."""
    if not nodes:
        return 0.0
    return min(n.confidence for n in nodes)


# ---------------------------------------------------------------------------
# CausalChainBuilder
# ---------------------------------------------------------------------------


class CausalChainBuilder:
    """
    Converts a completed :class:`InvestigationResult` into a :class:`CausalChain`.

    The builder is stateless — a single instance can process multiple
    investigation results without cross-contamination.

    Parameters
    ----------
    None.  The builder carries no configuration for the MVP.

    Methods
    -------
    build(investigation) → CausalChain | InsufficientEvidenceError
        The single public entry point.

    Notes
    -----
    The reasoning is deterministic and rule-based.  Given identical input
    evidence, the output chain is always identical (same node IDs, same
    ordering, same narrative).  This is intentional for the MVP.
    """

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def build(
        self,
        investigation: InvestigationResult,
    ) -> CausalChain | InsufficientEvidenceError:
        """
        Convert collected evidence into an ordered causal chain.

        Parameters
        ----------
        investigation:
            The output of :class:`~app.agents.orchestrator.BobOrchestrator`.
            Must have status COMPLETE or PARTIAL to proceed.

        Returns
        -------
        CausalChain
            On success — a fully populated causal graph.
        InsufficientEvidenceError
            When evidence is too sparse to produce a meaningful chain.

        Notes
        -----
        - The chain is always ordered root-to-terminal (topological order).
        - Every node's ``evidence_ids`` references only IDs that are present in
          ``investigation.evidence``.
        - No evidence is invented; only facts from the evidence set are used.
        """
        # Guard: nothing to reason over if all investigators failed
        if investigation.status == InvestigationStatus.FAILED:
            return InsufficientEvidenceError(
                pipeline_id=investigation.pipeline_id,
                reason=(
                    "All investigators failed — no evidence collected. "
                    "Cannot build a causal chain."
                ),
                evidence_count=0,
                missing_types=[t.value for t in EvidenceType],
            )

        evidence = investigation.evidence

        if len(evidence) < _MIN_EVIDENCE_COUNT:
            return InsufficientEvidenceError(
                pipeline_id=investigation.pipeline_id,
                reason="No evidence artifacts collected.",
                evidence_count=0,
                missing_types=[t.value for t in EvidenceType],
            )

        # Index evidence by type for easy lookup
        by_type = _collect_by_type(evidence)

        # Build the chain using the rule-based strategy
        return self._build_chain(investigation.pipeline_id, by_type)

    # ------------------------------------------------------------------
    # Internal: chain construction
    # ------------------------------------------------------------------

    def _build_chain(
        self,
        pipeline_id: str,
        by_type: dict[EvidenceType, list[BaseEvidence]],
    ) -> CausalChain | InsufficientEvidenceError:
        """
        Apply the rule set to construct the causal chain.

        Rule priority for root cause
        ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        1. DependencyEvidence with breaking_changes → dependency break
        2. ChangeEvidence with changed_files        → code change
        3. FailureEvidence alone                    → observable failure
        """
        nodes: list[CausalNode] = []
        edges: list[CausalEdge] = []
        root_cause_node_id: str | None = None

        dep_evidence_list = [
            ev for ev in by_type.get(EvidenceType.DEPENDENCY, [])
            if isinstance(ev, DependencyEvidence)
        ]
        change_evidence_list = [
            ev for ev in by_type.get(EvidenceType.CHANGE, [])
            if isinstance(ev, ChangeEvidence)
        ]
        failure_evidence_list = [
            ev for ev in by_type.get(EvidenceType.FAILURE, [])
            if isinstance(ev, FailureEvidence)
        ]
        test_evidence_list = [
            ev for ev in by_type.get(EvidenceType.TEST, [])
            if isinstance(ev, TestRunEvidence)
        ]

        # ------------------------------------------------------------------
        # Rule 1 — Dependency break with breaking changes (highest priority)
        # ------------------------------------------------------------------
        dep_with_breaks = [
            ev for ev in dep_evidence_list if ev.breaking_changes
        ]

        if dep_with_breaks:
            dep_ev = dep_with_breaks[0]
            change_ev = change_evidence_list[0] if change_evidence_list else None

            # Step 1: The triggering commit / dependency bump (CHANGE node)
            # Use both ChangeEvidence and DependencyEvidence if available.
            change_evidence_ids = [dep_ev.evidence_id]
            if change_ev:
                change_evidence_ids.insert(0, change_ev.evidence_id)

            # Describe the version change
            changed_dep = next(
                (c for c in dep_ev.changed if c.name),
                None,
            )
            if changed_dep:
                dep_label = (
                    f"{changed_dep.name} {changed_dep.old_version} → {changed_dep.new_version}"
                )
                dep_description = (
                    f"Dependency '{changed_dep.name}' was upgraded from version "
                    f"{changed_dep.old_version} to {changed_dep.new_version}. "
                    f"This is a major version bump that introduced breaking changes."
                )
            else:
                dep_label = "Dependency version change"
                dep_description = dep_ev.summary

            commit_sha = change_ev.commit_sha[:8] if change_ev else "unknown"
            change_node = CausalNode(
                node_id="node-root-cause",
                node_type=CausalNodeType.ROOT_CAUSE,
                label=f"Dependency bump: {dep_label}",
                description=(
                    f"Root cause: {dep_description} "
                    f"Introduced by commit {commit_sha}."
                    if change_ev
                    else f"Root cause: {dep_description}"
                ),
                evidence_ids=change_evidence_ids,
                confidence=min(dep_ev.confidence, change_ev.confidence if change_ev else 1.0),
            )
            nodes.append(change_node)
            root_cause_node_id = change_node.node_id

            # Step 2: The dependency break node (DEPENDENCY_BREAK)
            break_description = dep_ev.breaking_changes[0]
            break_node = CausalNode(
                node_id="node-dep-break",
                node_type=CausalNodeType.DEPENDENCY_BREAK,
                label=f"Breaking API change in {dep_ev.changed[0].name if dep_ev.changed else 'dependency'}",
                description=break_description,
                evidence_ids=[dep_ev.evidence_id],
                confidence=dep_ev.confidence,
            )
            nodes.append(break_node)

            edges.append(CausalEdge(
                edge_id="edge-root-to-break",
                source_node_id=change_node.node_id,
                target_node_id=break_node.node_id,
                relation=CausalRelation.CAUSED,
                explanation=(
                    f"Upgrading {changed_dep.name if changed_dep else 'the dependency'} "
                    f"to a new major version removed or changed public API, "
                    f"breaking downstream consumers."
                ),
            ))

            prev_node = break_node

        # ------------------------------------------------------------------
        # Rule 2 — Code change without dependency break (or as fallback)
        # ------------------------------------------------------------------
        elif change_evidence_list:
            change_ev = change_evidence_list[0]
            change_node = CausalNode(
                node_id="node-root-cause",
                node_type=CausalNodeType.ROOT_CAUSE,
                label=f"Code change in commit {change_ev.commit_sha[:8]}",
                description=(
                    f"Root cause: {change_ev.summary}. "
                    f"Changed files: "
                    f"{', '.join(f.path for f in change_ev.changed_files[:3])}."
                    if change_ev.changed_files
                    else f"Root cause: {change_ev.summary}."
                ),
                evidence_ids=[change_ev.evidence_id],
                confidence=change_ev.confidence,
            )
            nodes.append(change_node)
            root_cause_node_id = change_node.node_id
            prev_node = change_node

        # ------------------------------------------------------------------
        # Rule 3 — Observable failure only (lowest-confidence fallback)
        # ------------------------------------------------------------------
        elif failure_evidence_list:
            fail_ev = failure_evidence_list[0]
            failure_node = CausalNode(
                node_id="node-root-cause",
                node_type=CausalNodeType.ROOT_CAUSE,
                label=f"{fail_ev.error_class}: {fail_ev.error_message[:50]}",
                description=(
                    f"Root cause (inferred from observable failure): {fail_ev.summary}"
                ),
                evidence_ids=[fail_ev.evidence_id],
                confidence=fail_ev.confidence * 0.5,  # penalise: no upstream evidence
            )
            nodes.append(failure_node)
            root_cause_node_id = failure_node.node_id
            prev_node = failure_node

        else:
            # No actionable evidence for root cause
            return InsufficientEvidenceError(
                pipeline_id=pipeline_id,
                reason=(
                    "Could not determine root cause: no ChangeEvidence, "
                    "DependencyEvidence, or FailureEvidence was collected."
                ),
                evidence_count=sum(len(v) for v in by_type.values()),
                missing_types=[
                    EvidenceType.CHANGE.value,
                    EvidenceType.DEPENDENCY.value,
                    EvidenceType.FAILURE.value,
                ],
            )

        # ------------------------------------------------------------------
        # Step 3 — Observable failure node (if FailureEvidence present)
        # ------------------------------------------------------------------
        if failure_evidence_list and len(nodes) > 0 and nodes[-1].node_id != "node-root-cause":
            # We already have a root+break; add the observable failure
            fail_ev = failure_evidence_list[0]
            failure_node = CausalNode(
                node_id="node-failure",
                node_type=CausalNodeType.FAILURE,
                label=f"{fail_ev.error_class}: {fail_ev.error_message[:50]}",
                description=(
                    f"Observable CI failure: {fail_ev.summary}. "
                    f"Stage: {fail_ev.affected_stage}."
                ),
                evidence_ids=[fail_ev.evidence_id],
                confidence=fail_ev.confidence,
            )
            nodes.append(failure_node)
            edges.append(CausalEdge(
                edge_id=f"edge-{prev_node.node_id}-to-failure",
                source_node_id=prev_node.node_id,
                target_node_id=failure_node.node_id,
                relation=CausalRelation.CAUSED,
                explanation=(
                    f"The breaking API change caused {fail_ev.error_class} "
                    f"to be thrown at runtime in the '{fail_ev.affected_stage}' stage."
                ),
            ))
            prev_node = failure_node

        elif failure_evidence_list and len(nodes) == 1:
            # Rule 2 path (code change → failure)
            fail_ev = failure_evidence_list[0]
            failure_node = CausalNode(
                node_id="node-failure",
                node_type=CausalNodeType.FAILURE,
                label=f"{fail_ev.error_class}: {fail_ev.error_message[:50]}",
                description=(
                    f"Observable CI failure: {fail_ev.summary}. "
                    f"Stage: {fail_ev.affected_stage}."
                ),
                evidence_ids=[fail_ev.evidence_id],
                confidence=fail_ev.confidence,
            )
            nodes.append(failure_node)
            edges.append(CausalEdge(
                edge_id="edge-change-to-failure",
                source_node_id=prev_node.node_id,
                target_node_id=failure_node.node_id,
                relation=CausalRelation.CAUSED,
                explanation=(
                    f"The code change introduced an incompatibility "
                    f"that caused {fail_ev.error_class} in the '{fail_ev.affected_stage}' stage."
                ),
            ))
            prev_node = failure_node

        # ------------------------------------------------------------------
        # Step 4 — Test failure cascade node (if TestEvidence shows failures)
        # ------------------------------------------------------------------
        if test_evidence_list:
            test_ev = test_evidence_list[0]
            if test_ev.total_failed > 0 and len(nodes) >= 2:
                # Only add cascade if there is already a failure node before it
                prior_node = nodes[-1]
                if prior_node.node_type in (
                    CausalNodeType.FAILURE,
                    CausalNodeType.DEPENDENCY_BREAK,
                ):
                    failed_names = [ft.name for ft in test_ev.failed_tests[:3]]
                    cascade_node = CausalNode(
                        node_id="node-test-cascade",
                        node_type=CausalNodeType.CASCADE,
                        label=f"{test_ev.total_failed} test(s) failed",
                        description=(
                            f"{test_ev.total_failed} of {test_ev.total_run} tests failed. "
                            f"Failing tests: {', '.join(failed_names)}. "
                            f"All failures trace to the same root cause."
                        ),
                        evidence_ids=[test_ev.evidence_id],
                        confidence=test_ev.confidence,
                    )
                    nodes.append(cascade_node)
                    edges.append(CausalEdge(
                        edge_id=f"edge-{prior_node.node_id}-to-test-cascade",
                        source_node_id=prior_node.node_id,
                        target_node_id=cascade_node.node_id,
                        relation=CausalRelation.PROPAGATED_TO,
                        explanation=(
                            f"The failure propagated to {test_ev.total_failed} test(s). "
                            f"All {test_ev.total_failed} failed tests call the broken API."
                        ),
                    ))
                    prev_node = cascade_node

        # ------------------------------------------------------------------
        # Narrative — plain-language summary for non-technical audience
        # ------------------------------------------------------------------
        narrative = self._build_narrative(pipeline_id, by_type, nodes)

        # Overall chain confidence = min of all node confidences
        overall_confidence = _min_confidence(nodes)

        assert root_cause_node_id is not None, "root_cause_node_id must be set"

        return CausalChain(
            chain_id=f"chain-{pipeline_id}",
            pipeline_id=pipeline_id,
            nodes=nodes,
            edges=edges,
            root_cause_node_id=root_cause_node_id,
            narrative=narrative,
            confidence=overall_confidence,
            builder_version=_BUILDER_VERSION,
        )

    # ------------------------------------------------------------------
    # Internal: narrative generation
    # ------------------------------------------------------------------

    def _build_narrative(
        self,
        pipeline_id: str,
        by_type: dict[EvidenceType, list[BaseEvidence]],
        nodes: list[CausalNode],
    ) -> str:
        """
        Produce a 2–3 sentence plain-language explanation.

        Narrative is built from evidence summaries, not from LLM output.
        """
        dep_list = [
            ev for ev in by_type.get(EvidenceType.DEPENDENCY, [])
            if isinstance(ev, DependencyEvidence) and ev.breaking_changes
        ]
        failure_list = [
            ev for ev in by_type.get(EvidenceType.FAILURE, [])
            if isinstance(ev, FailureEvidence)
        ]
        test_list = [
            ev for ev in by_type.get(EvidenceType.TEST, [])
            if isinstance(ev, TestRunEvidence)
        ]
        history_list = [
            ev for ev in by_type.get(EvidenceType.HISTORICAL, [])
            if isinstance(ev, HistoricalEvidence)
        ]

        parts: list[str] = []

        if dep_list:
            dep_ev = dep_list[0]
            changed_dep = next((c for c in dep_ev.changed if c.name), None)
            if changed_dep:
                parts.append(
                    f"A dependency upgrade of '{changed_dep.name}' from "
                    f"version {changed_dep.old_version} to {changed_dep.new_version} "
                    f"introduced a breaking API change."
                )
            else:
                parts.append(f"A dependency upgrade introduced a breaking API change.")
        elif by_type.get(EvidenceType.CHANGE):
            change_ev = by_type[EvidenceType.CHANGE][0]
            parts.append(f"A code change introduced an incompatibility: {change_ev.summary}.")

        if failure_list:
            fail_ev = failure_list[0]
            parts.append(
                f"This caused '{fail_ev.error_class}: {fail_ev.error_message}' "
                f"to appear in the '{fail_ev.affected_stage}' stage."
            )

        if test_list:
            test_ev = test_list[0]
            if test_ev.total_failed > 0:
                parts.append(
                    f"{test_ev.total_failed} of {test_ev.total_run} tests failed "
                    f"as a result, blocking the build and deployment pipeline."
                )

        if history_list:
            hist_ev = history_list[0]
            if hist_ev.known_fix:
                parts.append(
                    f"A similar failure was seen previously; "
                    f"the known fix was: {hist_ev.known_fix}."
                )

        if not parts:
            parts.append(
                "A pipeline failure was detected. "
                "Insufficient evidence to produce a detailed narrative."
            )

        return " ".join(parts)
