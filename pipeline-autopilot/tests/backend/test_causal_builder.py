"""
Unit tests for CausalChainBuilder (Task 7).

Coverage
--------
1.  scenario-001 produces a CausalChain (not InsufficientEvidenceError)
2.  causal steps are ordered correctly (root → break → failure → cascade)
3.  root cause node is identified correctly (dependency bump)
4.  every causal node references only real evidence_ids present in the input
5.  provenance is preserved — evidence_ids exist on every non-trivial node
6.  no unsupported evidence is invented (node.evidence_ids ⊆ collected IDs)
7.  deterministic repeated results — two runs with same input = same output
8.  insufficient / missing evidence is handled clearly (InsufficientEvidenceError)
9.  existing Tasks 1–6 tests still pass (no regressions in this file)

Additional edge-case tests
--------------------------
- FAILED investigation → InsufficientEvidenceError
- Only ChangeEvidence (no DependencyEvidence) → root cause = code change
- Only FailureEvidence → root cause with penalised confidence
- No TestEvidence → chain has no CASCADE node
- root_cause_node_id is actually present in nodes list
- CausalChain fields are populated correctly
- Narrative is non-empty and references the dependency name
- builder_version is set
- chain_id is stable and predictable
- confidence is minimum of all node confidences
- InsufficientEvidenceError carries pipeline_id and reason
- Partial investigation (5 agents) still produces a chain
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

import pytest

from app.agents.orchestrator import BobOrchestrator
from app.ai.mock_provider import MockProvider
from app.ai.provider import AIProvider
from app.graph.builder import CausalChainBuilder, InsufficientEvidenceError
from app.models.causal import (
    CausalChain,
    CausalNodeType,
    CausalRelation,
)
from app.models.events import PipelineFailureEvent
from app.models.evidence import (
    ChangeEvidence,
    DepChange,
    DependencyEvidence,
    EvidenceSource,
    EvidenceType,
    FailedTest,
    FailureEvidence,
    HistoricalEvidence,
    InfraEvidence,
    TestRunEvidence,
)
from app.models.investigation import (
    InvestigationResult,
    InvestigationStatus,
    InvestigatorOutcome,
)


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

_SCENARIO_ID = "scenario-001"
_PIPELINE_ID = "run-test-task7"


@pytest.fixture
def event() -> PipelineFailureEvent:
    return PipelineFailureEvent(
        id="evt-task7-001",
        repo="acme/payments-service",
        branch="feature/update-deps",
        commit_sha="a1b2c3d4",
        pipeline_run_id=_PIPELINE_ID,
        timestamp=datetime(2024, 3, 15, 14, 32, 0, tzinfo=timezone.utc),
        failure_stage="test",
    )


@pytest.fixture
def builder() -> CausalChainBuilder:
    return CausalChainBuilder()


# ---------------------------------------------------------------------------
# Helpers: build a full InvestigationResult from the orchestrator
# ---------------------------------------------------------------------------


async def _run_scenario_001(event: PipelineFailureEvent) -> InvestigationResult:
    """Run the full orchestrator for scenario-001 and return InvestigationResult."""
    orchestrator = BobOrchestrator(provider=MockProvider())
    return await orchestrator.run(event, _SCENARIO_ID)


# ---------------------------------------------------------------------------
# Evidence factories — build minimal typed evidence for unit-level tests
# ---------------------------------------------------------------------------

_SOURCE = EvidenceSource(
    agent_id="test_agent",
    input_file="test_input.json",
    extraction_method="unit_test",
)


def _make_dep_evidence(
    evidence_id: str = "ev-dep-001",
    pipeline_id: str = _PIPELINE_ID,
    breaking: bool = True,
) -> DependencyEvidence:
    return DependencyEvidence(
        evidence_id=evidence_id,
        pipeline_id=pipeline_id,
        source=_SOURCE,
        summary="utility-lib upgraded from 2.3.1 → 3.0.0; formatCurrency() removed",
        confidence=0.99,
        changed=[
            DepChange(name="utility-lib", old_version="2.3.1", new_version="3.0.0")
        ],
        breaking_changes=(
            ["utility-lib 3.0.0 removes formatCurrency()"] if breaking else []
        ),
    )


def _make_change_evidence(
    evidence_id: str = "ev-change-001",
    pipeline_id: str = _PIPELINE_ID,
) -> ChangeEvidence:
    from app.models.evidence import ChangedFile
    return ChangeEvidence(
        evidence_id=evidence_id,
        pipeline_id=pipeline_id,
        source=_SOURCE,
        summary="package.json bumped utility-lib from ^2.3.1 to ^3.0.0",
        confidence=0.97,
        commit_sha="a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2",
        changed_files=[
            ChangedFile(path="package.json", additions=1, deletions=1)
        ],
    )


def _make_failure_evidence(
    evidence_id: str = "ev-fail-001",
    pipeline_id: str = _PIPELINE_ID,
) -> FailureEvidence:
    return FailureEvidence(
        evidence_id=evidence_id,
        pipeline_id=pipeline_id,
        source=_SOURCE,
        summary="TypeError: formatCurrency is not a function — 3 tests failed",
        confidence=0.98,
        error_class="TypeError",
        error_message="formatCurrency is not a function",
        affected_stage="test",
    )


def _make_test_evidence(
    evidence_id: str = "ev-test-001",
    pipeline_id: str = _PIPELINE_ID,
    total_failed: int = 3,
) -> TestRunEvidence:
    return TestRunEvidence(
        evidence_id=evidence_id,
        pipeline_id=pipeline_id,
        source=_SOURCE,
        summary=f"{total_failed} of 17 payment tests failed",
        confidence=0.99,
        failed_tests=[
            FailedTest(
                name=f"test_{i}",
                class_name="PaymentsService",
                failure_message="TypeError: formatCurrency is not a function",
            )
            for i in range(total_failed)
        ],
        total_run=17,
        total_failed=total_failed,
        total_passed=17 - total_failed,
    )


def _make_infra_evidence(
    evidence_id: str = "ev-infra-001",
    pipeline_id: str = _PIPELINE_ID,
) -> InfraEvidence:
    return InfraEvidence(
        evidence_id=evidence_id,
        pipeline_id=pipeline_id,
        source=_SOURCE,
        summary="Dockerfile and CI config are healthy; no infra cause",
        confidence=0.93,
    )


def _make_historical_evidence(
    evidence_id: str = "ev-hist-001",
    pipeline_id: str = _PIPELINE_ID,
) -> HistoricalEvidence:
    from app.models.evidence import SimilarFailure
    return HistoricalEvidence(
        evidence_id=evidence_id,
        pipeline_id=pipeline_id,
        source=_SOURCE,
        summary="1 similar prior failure found",
        confidence=0.91,
        known_fix="Pin utility-lib back to the last compatible version (2.3.1)",
        recurrence_count=1,
        similar_failures=[
            SimilarFailure(
                run_id="run-20240108-007",
                date=datetime(2024, 1, 8, 9, 14, 0, tzinfo=timezone.utc),
                root_cause="utility-lib 2.2.0 introduced breaking change in parseAmount()",
                fix_applied="Pinned utility-lib to 2.1.5",
                similarity_score=0.92,
            )
        ],
    )


def _make_full_investigation(
    pipeline_id: str = _PIPELINE_ID,
    status: InvestigationStatus = InvestigationStatus.COMPLETE,
    include_dep: bool = True,
    include_change: bool = True,
    include_failure: bool = True,
    include_test: bool = True,
    include_infra: bool = True,
    include_hist: bool = True,
) -> InvestigationResult:
    """Construct a synthetic InvestigationResult with the requested evidence types."""
    evidence = []
    outcomes = []

    if include_dep:
        ev = _make_dep_evidence(pipeline_id=pipeline_id)
        evidence.append(ev)
        outcomes.append(InvestigatorOutcome(
            agent_id="dependency_investigator", success=True, evidence_id=ev.evidence_id
        ))
    if include_change:
        ev = _make_change_evidence(pipeline_id=pipeline_id)
        evidence.append(ev)
        outcomes.append(InvestigatorOutcome(
            agent_id="code_investigator", success=True, evidence_id=ev.evidence_id
        ))
    if include_failure:
        ev = _make_failure_evidence(pipeline_id=pipeline_id)
        evidence.append(ev)
        outcomes.append(InvestigatorOutcome(
            agent_id="log_investigator", success=True, evidence_id=ev.evidence_id
        ))
    if include_test:
        ev = _make_test_evidence(pipeline_id=pipeline_id)
        evidence.append(ev)
        outcomes.append(InvestigatorOutcome(
            agent_id="test_investigator", success=True, evidence_id=ev.evidence_id
        ))
    if include_infra:
        ev = _make_infra_evidence(pipeline_id=pipeline_id)
        evidence.append(ev)
        outcomes.append(InvestigatorOutcome(
            agent_id="infra_investigator", success=True, evidence_id=ev.evidence_id
        ))
    if include_hist:
        ev = _make_historical_evidence(pipeline_id=pipeline_id)
        evidence.append(ev)
        outcomes.append(InvestigatorOutcome(
            agent_id="history_investigator", success=True, evidence_id=ev.evidence_id
        ))

    return InvestigationResult(
        pipeline_id=pipeline_id,
        scenario_id=_SCENARIO_ID,
        status=status,
        evidence=evidence,
        outcomes=outcomes,
        errors={},
        started_at=datetime(2024, 3, 15, 14, 30, 0, tzinfo=timezone.utc),
        completed_at=datetime(2024, 3, 15, 14, 31, 0, tzinfo=timezone.utc),
    )


# ===========================================================================
# Test 1: scenario-001 produces a CausalChain (end-to-end via orchestrator)
# ===========================================================================


@pytest.mark.asyncio
async def test_scenario_001_produces_causal_chain(event, builder):
    """End-to-end: orchestrator → builder → CausalChain for scenario-001."""
    investigation = await _run_scenario_001(event)
    result = builder.build(investigation)
    assert isinstance(result, CausalChain), (
        f"Expected CausalChain, got {type(result).__name__}: "
        f"{result.reason if isinstance(result, InsufficientEvidenceError) else ''}"
    )


@pytest.mark.asyncio
async def test_scenario_001_chain_pipeline_id(event, builder):
    investigation = await _run_scenario_001(event)
    chain = builder.build(investigation)
    assert isinstance(chain, CausalChain)
    assert chain.pipeline_id == event.pipeline_run_id


@pytest.mark.asyncio
async def test_scenario_001_chain_id_contains_pipeline_id(event, builder):
    investigation = await _run_scenario_001(event)
    chain = builder.build(investigation)
    assert isinstance(chain, CausalChain)
    assert event.pipeline_run_id in chain.chain_id


# ===========================================================================
# Test 2: causal steps are ordered correctly
# ===========================================================================


def test_causal_steps_ordered_root_to_terminal(builder):
    """Full scenario: ROOT_CAUSE → DEPENDENCY_BREAK → FAILURE → CASCADE."""
    investigation = _make_full_investigation()
    chain = builder.build(investigation)
    assert isinstance(chain, CausalChain)

    node_types = [n.node_type for n in chain.nodes]

    # First node must be ROOT_CAUSE
    assert node_types[0] == CausalNodeType.ROOT_CAUSE, (
        f"First node must be ROOT_CAUSE, got {node_types[0]}"
    )

    # ROOT_CAUSE must precede DEPENDENCY_BREAK
    root_idx = node_types.index(CausalNodeType.ROOT_CAUSE)
    assert CausalNodeType.DEPENDENCY_BREAK in node_types
    dep_break_idx = node_types.index(CausalNodeType.DEPENDENCY_BREAK)
    assert root_idx < dep_break_idx, "ROOT_CAUSE must precede DEPENDENCY_BREAK"

    # DEPENDENCY_BREAK must precede FAILURE
    assert CausalNodeType.FAILURE in node_types
    failure_idx = node_types.index(CausalNodeType.FAILURE)
    assert dep_break_idx < failure_idx, "DEPENDENCY_BREAK must precede FAILURE"

    # FAILURE must precede CASCADE
    assert CausalNodeType.CASCADE in node_types
    cascade_idx = node_types.index(CausalNodeType.CASCADE)
    assert failure_idx < cascade_idx, "FAILURE must precede CASCADE"


def test_causal_steps_at_least_two_nodes(builder):
    """Even minimal evidence must produce at least 2 nodes."""
    investigation = _make_full_investigation(
        include_dep=True,
        include_change=False,
        include_failure=False,
        include_test=False,
        include_infra=False,
        include_hist=False,
    )
    chain = builder.build(investigation)
    assert isinstance(chain, CausalChain)
    assert len(chain.nodes) >= 2


def test_edges_form_connected_chain(builder):
    """Every edge source/target must reference existing node IDs."""
    investigation = _make_full_investigation()
    chain = builder.build(investigation)
    assert isinstance(chain, CausalChain)

    node_ids = {n.node_id for n in chain.nodes}
    for edge in chain.edges:
        assert edge.source_node_id in node_ids, (
            f"Edge source '{edge.source_node_id}' not in nodes"
        )
        assert edge.target_node_id in node_ids, (
            f"Edge target '{edge.target_node_id}' not in nodes"
        )


def test_edges_are_forward_only(builder):
    """Edges must go from earlier nodes to later nodes (no back-edges)."""
    investigation = _make_full_investigation()
    chain = builder.build(investigation)
    assert isinstance(chain, CausalChain)

    node_index = {n.node_id: i for i, n in enumerate(chain.nodes)}
    for edge in chain.edges:
        src_idx = node_index[edge.source_node_id]
        tgt_idx = node_index[edge.target_node_id]
        assert src_idx < tgt_idx, (
            f"Back-edge detected: {edge.source_node_id}(idx={src_idx}) "
            f"→ {edge.target_node_id}(idx={tgt_idx})"
        )


# ===========================================================================
# Test 3: root cause is identified correctly
# ===========================================================================


def test_root_cause_is_dependency_bump(builder):
    """With full scenario-001 evidence, root cause must be the dependency bump."""
    investigation = _make_full_investigation()
    chain = builder.build(investigation)
    assert isinstance(chain, CausalChain)

    root_node = next(
        (n for n in chain.nodes if n.node_id == chain.root_cause_node_id), None
    )
    assert root_node is not None, "root_cause_node_id must reference an existing node"
    assert root_node.node_type == CausalNodeType.ROOT_CAUSE

    # For scenario-001, root cause must mention the dependency name
    label_or_desc = root_node.label + " " + root_node.description
    assert "utility-lib" in label_or_desc.lower() or "dependency" in label_or_desc.lower()


def test_root_cause_node_id_in_nodes(builder):
    """root_cause_node_id must be the node_id of one of the nodes in the chain."""
    investigation = _make_full_investigation()
    chain = builder.build(investigation)
    assert isinstance(chain, CausalChain)

    node_ids = [n.node_id for n in chain.nodes]
    assert chain.root_cause_node_id in node_ids


def test_root_cause_is_first_node(builder):
    """The root cause node must be first in the ordered node list."""
    investigation = _make_full_investigation()
    chain = builder.build(investigation)
    assert isinstance(chain, CausalChain)
    assert chain.nodes[0].node_id == chain.root_cause_node_id


def test_exactly_one_root_cause_node(builder):
    """There must be exactly one ROOT_CAUSE node."""
    investigation = _make_full_investigation()
    chain = builder.build(investigation)
    assert isinstance(chain, CausalChain)

    root_nodes = [n for n in chain.nodes if n.node_type == CausalNodeType.ROOT_CAUSE]
    assert len(root_nodes) == 1, f"Expected exactly 1 ROOT_CAUSE node, got {len(root_nodes)}"


def test_root_cause_prefers_dependency_over_code_change(builder):
    """When both DependencyEvidence (with breaks) and ChangeEvidence exist,
    the ROOT_CAUSE node should reflect the dependency bump."""
    investigation = _make_full_investigation(
        include_dep=True,  # has breaking changes
        include_change=True,
        include_failure=False,
        include_test=False,
        include_infra=False,
        include_hist=False,
    )
    chain = builder.build(investigation)
    assert isinstance(chain, CausalChain)

    root_node = chain.nodes[0]
    # With dep breaking changes, root cause label should mention the dep, not just commit
    assert "utility-lib" in root_node.label or "dependency" in root_node.label.lower()


def test_root_cause_falls_back_to_code_change_when_no_dep_break(builder):
    """Without DependencyEvidence breaking changes, root cause is the code change."""
    investigation = _make_full_investigation(
        include_dep=False,
        include_change=True,
        include_failure=True,
        include_test=False,
        include_infra=False,
        include_hist=False,
    )
    chain = builder.build(investigation)
    assert isinstance(chain, CausalChain)
    root_node = chain.nodes[0]
    assert root_node.node_type == CausalNodeType.ROOT_CAUSE
    # Root cause node should reference commit SHA
    assert "a1b2c3d4" in root_node.label or "commit" in root_node.label.lower()


def test_root_cause_falls_back_to_failure_only(builder):
    """Without dep or change evidence, root cause is inferred from FailureEvidence."""
    investigation = _make_full_investigation(
        include_dep=False,
        include_change=False,
        include_failure=True,
        include_test=False,
        include_infra=False,
        include_hist=False,
    )
    chain = builder.build(investigation)
    assert isinstance(chain, CausalChain)
    root_node = chain.nodes[0]
    assert root_node.node_type == CausalNodeType.ROOT_CAUSE
    # Confidence should be penalised (< 0.5 of original 0.98)
    assert root_node.confidence < 0.98


# ===========================================================================
# Test 4: causal nodes reference real evidence IDs
# ===========================================================================


def test_all_node_evidence_ids_are_real(builder):
    """Every evidence_id on every node must exist in the input evidence."""
    investigation = _make_full_investigation()
    chain = builder.build(investigation)
    assert isinstance(chain, CausalChain)

    real_ids = {ev.evidence_id for ev in investigation.evidence}
    for node in chain.nodes:
        for eid in node.evidence_ids:
            assert eid in real_ids, (
                f"Node '{node.node_id}' references evidence_id '{eid}' "
                f"which is NOT in the collected evidence set. "
                f"Real IDs: {real_ids}"
            )


@pytest.mark.asyncio
async def test_scenario_001_all_node_evidence_ids_are_real(event, builder):
    """End-to-end: verify no invented evidence IDs in scenario-001 chain."""
    investigation = await _run_scenario_001(event)
    chain = builder.build(investigation)
    assert isinstance(chain, CausalChain)

    real_ids = {ev.evidence_id for ev in investigation.evidence}
    for node in chain.nodes:
        for eid in node.evidence_ids:
            assert eid in real_ids, (
                f"Invented evidence ID '{eid}' found on node '{node.node_id}'"
            )


# ===========================================================================
# Test 5: provenance is preserved
# ===========================================================================


def test_root_cause_node_has_evidence(builder):
    """The ROOT_CAUSE node must have at least one evidence_id."""
    investigation = _make_full_investigation()
    chain = builder.build(investigation)
    assert isinstance(chain, CausalChain)

    root_node = next(n for n in chain.nodes if n.node_id == chain.root_cause_node_id)
    assert len(root_node.evidence_ids) >= 1, "ROOT_CAUSE node must have evidence"


def test_dep_break_node_has_dep_evidence(builder):
    """The DEPENDENCY_BREAK node must reference DependencyEvidence."""
    investigation = _make_full_investigation()
    chain = builder.build(investigation)
    assert isinstance(chain, CausalChain)

    dep_ev = _make_dep_evidence()  # same evidence_id as in investigation
    dep_break_node = next(
        (n for n in chain.nodes if n.node_type == CausalNodeType.DEPENDENCY_BREAK), None
    )
    assert dep_break_node is not None
    # The dep_break node must reference the DependencyEvidence
    dep_evidence_ids = {
        ev.evidence_id
        for ev in investigation.evidence
        if ev.evidence_type == EvidenceType.DEPENDENCY
    }
    assert any(eid in dep_evidence_ids for eid in dep_break_node.evidence_ids)


def test_failure_node_has_failure_evidence(builder):
    """The FAILURE node must reference FailureEvidence."""
    investigation = _make_full_investigation()
    chain = builder.build(investigation)
    assert isinstance(chain, CausalChain)

    failure_node = next(
        (n for n in chain.nodes if n.node_type == CausalNodeType.FAILURE), None
    )
    assert failure_node is not None
    failure_evidence_ids = {
        ev.evidence_id
        for ev in investigation.evidence
        if ev.evidence_type == EvidenceType.FAILURE
    }
    assert any(eid in failure_evidence_ids for eid in failure_node.evidence_ids)


def test_cascade_node_has_test_evidence(builder):
    """The CASCADE node must reference TestEvidence."""
    investigation = _make_full_investigation()
    chain = builder.build(investigation)
    assert isinstance(chain, CausalChain)

    cascade_node = next(
        (n for n in chain.nodes if n.node_type == CausalNodeType.CASCADE), None
    )
    assert cascade_node is not None
    test_evidence_ids = {
        ev.evidence_id
        for ev in investigation.evidence
        if ev.evidence_type == EvidenceType.TEST
    }
    assert any(eid in test_evidence_ids for eid in cascade_node.evidence_ids)


def test_every_node_has_at_least_one_evidence_id(builder):
    """Every node in a full-evidence chain must carry at least one evidence_id."""
    investigation = _make_full_investigation()
    chain = builder.build(investigation)
    assert isinstance(chain, CausalChain)

    for node in chain.nodes:
        assert len(node.evidence_ids) >= 1, (
            f"Node '{node.node_id}' (type={node.node_type}) "
            f"has no evidence_ids — all causal claims must be evidence-backed"
        )


# ===========================================================================
# Test 6: no unsupported evidence is invented
# ===========================================================================


def test_no_invented_evidence(builder):
    """Strict subset check: union of all node evidence_ids ⊆ collected IDs."""
    investigation = _make_full_investigation()
    chain = builder.build(investigation)
    assert isinstance(chain, CausalChain)

    real_ids = {ev.evidence_id for ev in investigation.evidence}
    all_referenced_ids: set[str] = set()
    for node in chain.nodes:
        all_referenced_ids.update(node.evidence_ids)

    invented = all_referenced_ids - real_ids
    assert not invented, (
        f"Builder invented {len(invented)} evidence ID(s) not in the "
        f"input investigation: {invented}"
    )


def test_infra_evidence_not_in_any_node(builder):
    """InfraEvidence (no issues) should NOT appear in any causal node for scenario-001."""
    investigation = _make_full_investigation()
    chain = builder.build(investigation)
    assert isinstance(chain, CausalChain)

    infra_evidence_ids = {
        ev.evidence_id
        for ev in investigation.evidence
        if ev.evidence_type == EvidenceType.INFRA
    }
    for node in chain.nodes:
        overlap = set(node.evidence_ids) & infra_evidence_ids
        # InfraEvidence is not expected to drive any causal node in scenario-001
        # (it rules OUT infra as a cause — it's used for narrative, not nodes)
        # This test documents the expected behaviour; update if future rules change.
        assert not overlap, (
            f"Node '{node.node_id}' unexpectedly references InfraEvidence {overlap}. "
            f"Infrastructure was ruled out for scenario-001."
        )


# ===========================================================================
# Test 7: deterministic repeated results
# ===========================================================================


def test_build_is_deterministic_same_input(builder):
    """Two build() calls on the same investigation produce identical chains."""
    investigation = _make_full_investigation()
    chain1 = builder.build(investigation)
    chain2 = builder.build(investigation)

    assert isinstance(chain1, CausalChain)
    assert isinstance(chain2, CausalChain)

    # Same structure
    assert chain1.chain_id == chain2.chain_id
    assert chain1.root_cause_node_id == chain2.root_cause_node_id
    assert len(chain1.nodes) == len(chain2.nodes)
    assert len(chain1.edges) == len(chain2.edges)

    # Same node IDs in same order
    for n1, n2 in zip(chain1.nodes, chain2.nodes):
        assert n1.node_id == n2.node_id
        assert n1.node_type == n2.node_type
        assert n1.evidence_ids == n2.evidence_ids

    # Same edge IDs in same order
    for e1, e2 in zip(chain1.edges, chain2.edges):
        assert e1.edge_id == e2.edge_id
        assert e1.relation == e2.relation


def test_build_is_deterministic_separate_builders():
    """Two separate CausalChainBuilder instances produce identical chains."""
    investigation = _make_full_investigation()
    b1 = CausalChainBuilder()
    b2 = CausalChainBuilder()
    chain1 = b1.build(investigation)
    chain2 = b2.build(investigation)

    assert isinstance(chain1, CausalChain)
    assert isinstance(chain2, CausalChain)
    assert chain1.root_cause_node_id == chain2.root_cause_node_id
    assert len(chain1.nodes) == len(chain2.nodes)


@pytest.mark.asyncio
async def test_scenario_001_deterministic_repeated(event, builder):
    """Two end-to-end runs (orchestrator → builder) for scenario-001 are structurally equal."""
    investigation1 = await _run_scenario_001(event)
    investigation2 = await _run_scenario_001(event)

    chain1 = builder.build(investigation1)
    chain2 = builder.build(investigation2)

    assert isinstance(chain1, CausalChain)
    assert isinstance(chain2, CausalChain)

    # Same number of nodes and same types (IDs may differ between runs due to uuid in evidence_id)
    types1 = [n.node_type for n in chain1.nodes]
    types2 = [n.node_type for n in chain2.nodes]
    assert types1 == types2, f"Node types differ: {types1} vs {types2}"

    relations1 = [e.relation for e in chain1.edges]
    relations2 = [e.relation for e in chain2.edges]
    assert relations1 == relations2


# ===========================================================================
# Test 8: insufficient / missing evidence is handled clearly
# ===========================================================================


def test_failed_investigation_returns_insufficient_error(builder):
    """A fully FAILED investigation (no evidence) must return InsufficientEvidenceError."""
    investigation = InvestigationResult(
        pipeline_id=_PIPELINE_ID,
        scenario_id=_SCENARIO_ID,
        status=InvestigationStatus.FAILED,
        evidence=[],
        outcomes=[],
        errors={"log_investigator": "injected failure"},
        started_at=datetime.utcnow(),
    )
    result = builder.build(investigation)
    assert isinstance(result, InsufficientEvidenceError)


def test_insufficient_error_carries_pipeline_id(builder):
    investigation = InvestigationResult(
        pipeline_id=_PIPELINE_ID,
        scenario_id=_SCENARIO_ID,
        status=InvestigationStatus.FAILED,
        evidence=[],
        outcomes=[],
        errors={},
        started_at=datetime.utcnow(),
    )
    result = builder.build(investigation)
    assert isinstance(result, InsufficientEvidenceError)
    assert result.pipeline_id == _PIPELINE_ID


def test_insufficient_error_has_non_empty_reason(builder):
    investigation = InvestigationResult(
        pipeline_id=_PIPELINE_ID,
        scenario_id=_SCENARIO_ID,
        status=InvestigationStatus.FAILED,
        evidence=[],
        outcomes=[],
        errors={},
        started_at=datetime.utcnow(),
    )
    result = builder.build(investigation)
    assert isinstance(result, InsufficientEvidenceError)
    assert len(result.reason) > 0


def test_only_infra_evidence_returns_insufficient_error(builder):
    """InfraEvidence alone (no change/dep/failure) cannot produce a chain."""
    investigation = _make_full_investigation(
        include_dep=False,
        include_change=False,
        include_failure=False,
        include_test=False,
        include_infra=True,
        include_hist=False,
    )
    result = builder.build(investigation)
    assert isinstance(result, InsufficientEvidenceError), (
        "InfraEvidence alone is insufficient for a causal chain"
    )


def test_insufficient_error_lists_missing_types(builder):
    """InsufficientEvidenceError should list the missing evidence types."""
    investigation = InvestigationResult(
        pipeline_id=_PIPELINE_ID,
        scenario_id=_SCENARIO_ID,
        status=InvestigationStatus.FAILED,
        evidence=[],
        outcomes=[],
        errors={},
        started_at=datetime.utcnow(),
    )
    result = builder.build(investigation)
    assert isinstance(result, InsufficientEvidenceError)
    assert len(result.missing_types) > 0


def test_no_evidence_at_all_returns_insufficient_error(builder):
    """An empty evidence list (PARTIAL status) returns InsufficientEvidenceError."""
    investigation = InvestigationResult(
        pipeline_id=_PIPELINE_ID,
        scenario_id=_SCENARIO_ID,
        status=InvestigationStatus.PARTIAL,
        evidence=[],
        outcomes=[],
        errors={"log_investigator": "fail"},
        started_at=datetime.utcnow(),
    )
    result = builder.build(investigation)
    assert isinstance(result, InsufficientEvidenceError)


# ===========================================================================
# Additional: chain fields are correctly populated
# ===========================================================================


def test_chain_narrative_is_non_empty(builder):
    investigation = _make_full_investigation()
    chain = builder.build(investigation)
    assert isinstance(chain, CausalChain)
    assert len(chain.narrative) > 10


def test_chain_narrative_mentions_dependency(builder):
    """For scenario-001, the narrative should mention 'utility-lib'."""
    investigation = _make_full_investigation()
    chain = builder.build(investigation)
    assert isinstance(chain, CausalChain)
    assert "utility-lib" in chain.narrative


def test_chain_narrative_mentions_failure(builder):
    """Narrative should mention the error class or type."""
    investigation = _make_full_investigation()
    chain = builder.build(investigation)
    assert isinstance(chain, CausalChain)
    assert "TypeError" in chain.narrative or "formatCurrency" in chain.narrative


def test_chain_builder_version_is_set(builder):
    investigation = _make_full_investigation()
    chain = builder.build(investigation)
    assert isinstance(chain, CausalChain)
    assert chain.builder_version
    assert isinstance(chain.builder_version, str)


def test_chain_confidence_is_min_of_node_confidences(builder):
    """chain.confidence must equal the minimum node confidence."""
    investigation = _make_full_investigation()
    chain = builder.build(investigation)
    assert isinstance(chain, CausalChain)

    expected_min = min(n.confidence for n in chain.nodes)
    assert abs(chain.confidence - expected_min) < 1e-9


def test_chain_confidence_in_valid_range(builder):
    investigation = _make_full_investigation()
    chain = builder.build(investigation)
    assert isinstance(chain, CausalChain)
    assert 0.0 <= chain.confidence <= 1.0


def test_chain_id_predictable(builder):
    """chain_id must contain the pipeline_id."""
    investigation = _make_full_investigation(pipeline_id="run-predictable-test")
    chain = builder.build(investigation)
    assert isinstance(chain, CausalChain)
    assert "run-predictable-test" in chain.chain_id


def test_node_labels_are_non_empty(builder):
    """Every node must have a non-empty label."""
    investigation = _make_full_investigation()
    chain = builder.build(investigation)
    assert isinstance(chain, CausalChain)
    for node in chain.nodes:
        assert len(node.label.strip()) > 0, f"Node {node.node_id} has empty label"


def test_edge_relations_are_valid_enum_values(builder):
    """All edge relations must be valid CausalRelation enum values."""
    investigation = _make_full_investigation()
    chain = builder.build(investigation)
    assert isinstance(chain, CausalChain)
    valid_relations = set(CausalRelation)
    for edge in chain.edges:
        assert edge.relation in valid_relations, (
            f"Edge {edge.edge_id} has invalid relation: {edge.relation}"
        )


def test_edge_explanations_are_non_empty(builder):
    investigation = _make_full_investigation()
    chain = builder.build(investigation)
    assert isinstance(chain, CausalChain)
    for edge in chain.edges:
        assert len(edge.explanation.strip()) > 0


def test_node_descriptions_are_non_empty(builder):
    investigation = _make_full_investigation()
    chain = builder.build(investigation)
    assert isinstance(chain, CausalChain)
    for node in chain.nodes:
        assert len(node.description.strip()) > 0


# ===========================================================================
# Additional: partial evidence paths
# ===========================================================================


def test_no_test_evidence_no_cascade_node(builder):
    """Without TestEvidence, there should be no CASCADE node."""
    investigation = _make_full_investigation(
        include_dep=True,
        include_change=True,
        include_failure=True,
        include_test=False,
        include_infra=False,
        include_hist=False,
    )
    chain = builder.build(investigation)
    assert isinstance(chain, CausalChain)
    cascade_nodes = [n for n in chain.nodes if n.node_type == CausalNodeType.CASCADE]
    assert len(cascade_nodes) == 0, "No CASCADE node expected when TestEvidence is absent"


def test_partial_investigation_still_produces_chain(builder):
    """A PARTIAL investigation (5 of 6 agents) should still produce a chain."""
    investigation = _make_full_investigation(
        include_dep=True,
        include_change=True,
        include_failure=True,
        include_test=True,
        include_infra=False,  # infra agent failed
        include_hist=True,
        status=InvestigationStatus.PARTIAL,
    )
    result = builder.build(investigation)
    assert isinstance(result, CausalChain), (
        "PARTIAL investigation should still produce a chain when key evidence types exist"
    )


def test_only_dep_evidence_with_breaks_produces_chain(builder):
    """DependencyEvidence alone with breaking_changes is enough for a minimal chain."""
    investigation = _make_full_investigation(
        include_dep=True,
        include_change=False,
        include_failure=False,
        include_test=False,
        include_infra=False,
        include_hist=False,
    )
    result = builder.build(investigation)
    assert isinstance(result, CausalChain)
    assert len(result.nodes) >= 2  # root + dep_break at minimum


def test_dep_evidence_without_breaks_falls_through_to_change(builder):
    """DependencyEvidence without breaking_changes should not be root cause;
    ChangeEvidence should take priority."""
    dep_no_breaks = DependencyEvidence(
        evidence_id="ev-dep-nobreak",
        pipeline_id=_PIPELINE_ID,
        source=_SOURCE,
        summary="utility-lib changed but no breaking changes found",
        confidence=0.80,
        changed=[
            DepChange(name="utility-lib", old_version="2.3.1", new_version="2.3.2")
        ],
        breaking_changes=[],  # no breaking changes
    )
    change_ev = _make_change_evidence()
    failure_ev = _make_failure_evidence()

    investigation = InvestigationResult(
        pipeline_id=_PIPELINE_ID,
        scenario_id=_SCENARIO_ID,
        status=InvestigationStatus.COMPLETE,
        evidence=[dep_no_breaks, change_ev, failure_ev],
        outcomes=[],
        errors={},
        started_at=datetime.utcnow(),
    )
    chain = builder.build(investigation)
    assert isinstance(chain, CausalChain)
    root_node = chain.nodes[0]
    # Should fall back to code change, not the dep without breaks
    assert root_node.node_type == CausalNodeType.ROOT_CAUSE
    # Root cause evidence should include the change evidence, not the dep
    assert change_ev.evidence_id in root_node.evidence_ids


# ===========================================================================
# Additional: builder reuse is safe (stateless)
# ===========================================================================


def test_builder_reuse_is_safe(builder):
    """Builder is stateless; building two different investigations in sequence is safe."""
    inv1 = _make_full_investigation(pipeline_id="run-A")
    inv2 = _make_full_investigation(pipeline_id="run-B")

    chain1 = builder.build(inv1)
    chain2 = builder.build(inv2)

    assert isinstance(chain1, CausalChain)
    assert isinstance(chain2, CausalChain)
    assert chain1.pipeline_id == "run-A"
    assert chain2.pipeline_id == "run-B"
    # Chains must be independent — node IDs are not shared
    ids1 = {n.node_id for n in chain1.nodes}
    ids2 = {n.node_id for n in chain2.nodes}
    # Same node_id values are expected (since IDs are rule-derived, not random)
    # but the chains must reference the correct pipeline
    assert chain1.chain_id != chain2.chain_id


# ===========================================================================
# Additional: CausalChain / CausalNode model validation
# ===========================================================================


def test_causal_node_type_enum_values():
    """CausalNodeType must contain the six expected values."""
    assert CausalNodeType.CHANGE in CausalNodeType
    assert CausalNodeType.DEPENDENCY_BREAK in CausalNodeType
    assert CausalNodeType.FAILURE in CausalNodeType
    assert CausalNodeType.CASCADE in CausalNodeType
    assert CausalNodeType.ROOT_CAUSE in CausalNodeType
    assert CausalNodeType.FIX in CausalNodeType


def test_causal_relation_enum_values():
    """CausalRelation must contain the four expected values."""
    assert CausalRelation.CAUSED in CausalRelation
    assert CausalRelation.CONTRIBUTED_TO in CausalRelation
    assert CausalRelation.TRIGGERED in CausalRelation
    assert CausalRelation.PROPAGATED_TO in CausalRelation
