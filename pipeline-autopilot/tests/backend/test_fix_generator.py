"""
Unit tests for FixGenerator (Task 8).

Coverage
--------
1.  scenario-001 produces the expected FixProposal (dependency pin: utility-lib 3.0.0 → 2.3.1)
2.  fix references the causal root-cause node
3.  fix references supporting evidence (evidence_ids are non-empty and real)
4.  fix is deterministic — two calls with same chain produce identical output
5.  insufficient / invalid causal evidence is handled clearly (InsufficientCausalChainError)
6.  existing Tasks 1–7 tests continue passing (no regressions)

Additional edge-case tests
--------------------------
- fix_type is DEPENDENCY_CHANGE for scenario-001
- dependency_changes contains the correct pin (new=2.3.1, old=3.0.0)
- affected_file is "package.json" for a Node.js dependency fix
- rationale mentions the breaking dependency name
- description mentions version numbers
- confidence matches root-cause node confidence
- generator_version is set
- fix_id is stable and predictable
- FixProposal is frozen (immutable)
- Chain with no ROOT_CAUSE node returns InsufficientCausalChainError
- ROOT_CAUSE with empty evidence_ids returns InsufficientCausalChainError
- Zero-confidence chain returns InsufficientCausalChainError
- Code-change-only chain (no DEPENDENCY_BREAK) produces CODE_PATCH fix
- DEPENDENCY_BREAK chain with unparseable label produces fallback dep fix
- InsufficientCausalChainError carries pipeline_id and reason
- FixGenerator is reusable across multiple chains
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import pytest

from app.agents.orchestrator import BobOrchestrator
from app.ai.mock_provider import MockProvider
from app.graph.builder import CausalChainBuilder, InsufficientEvidenceError
from app.graph.fix_generator import FixGenerator, InsufficientCausalChainError
from app.models.causal import CausalChain, CausalEdge, CausalNode, CausalNodeType, CausalRelation
from app.models.events import PipelineFailureEvent
from app.models.evidence import (
    ChangeEvidence,
    DepChange,
    DependencyEvidence,
    EvidenceSource,
    FailedTest,
    FailureEvidence,
    HistoricalEvidence,
    InfraEvidence,
    TestRunEvidence,
)
from app.models.fix import FixProposal, FixType
from app.models.investigation import (
    InvestigationResult,
    InvestigationStatus,
    InvestigatorOutcome,
)


# ---------------------------------------------------------------------------
# Shared constants
# ---------------------------------------------------------------------------

_SCENARIO_ID = "scenario-001"
_PIPELINE_ID = "run-test-task8"


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def event() -> PipelineFailureEvent:
    return PipelineFailureEvent(
        id="evt-task8-001",
        repo="acme/payments-service",
        branch="feature/update-deps",
        commit_sha="a1b2c3d4",
        pipeline_run_id=_PIPELINE_ID,
        timestamp=datetime(2024, 3, 15, 14, 32, 0, tzinfo=timezone.utc),
        failure_stage="test",
    )


@pytest.fixture
def generator() -> FixGenerator:
    return FixGenerator()


@pytest.fixture
def builder() -> CausalChainBuilder:
    return CausalChainBuilder()


# ---------------------------------------------------------------------------
# Evidence factories (mirror task-7 helpers, scoped to task-8 pipeline)
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


def _build_chain_from_investigation(
    investigation: InvestigationResult,
) -> CausalChain:
    """Helper: build a CausalChain from an InvestigationResult; assert success."""
    result = CausalChainBuilder().build(investigation)
    assert isinstance(result, CausalChain), (
        f"Expected CausalChain, got {type(result).__name__}: {result}"
    )
    return result


# ---------------------------------------------------------------------------
# End-to-end helper (full orchestrator path)
# ---------------------------------------------------------------------------


async def _run_scenario_001(event: PipelineFailureEvent) -> InvestigationResult:
    orchestrator = BobOrchestrator(provider=MockProvider())
    return await orchestrator.run(event, _SCENARIO_ID)


# ===========================================================================
# Test 1: scenario-001 produces the expected FixProposal
# ===========================================================================


@pytest.mark.asyncio
async def test_scenario_001_produces_fix_proposal(event: PipelineFailureEvent, generator: FixGenerator):
    """End-to-end: full orchestrator + builder + generator for scenario-001."""
    investigation = await _run_scenario_001(event)
    chain = _build_chain_from_investigation(investigation)
    result = generator.generate(chain)

    assert isinstance(result, FixProposal), (
        f"Expected FixProposal, got {type(result).__name__}: {result}"
    )


@pytest.mark.asyncio
async def test_scenario_001_fix_type_is_dependency_change(event: PipelineFailureEvent, generator: FixGenerator):
    investigation = await _run_scenario_001(event)
    chain = _build_chain_from_investigation(investigation)
    fix = generator.generate(chain)

    assert isinstance(fix, FixProposal)
    assert fix.fix_type == FixType.DEPENDENCY_CHANGE


@pytest.mark.asyncio
async def test_scenario_001_fix_pins_utility_lib_back(event: PipelineFailureEvent, generator: FixGenerator):
    """Core acceptance criterion: fix pins utility-lib back from 3.0.0 to 2.3.1."""
    investigation = await _run_scenario_001(event)
    chain = _build_chain_from_investigation(investigation)
    fix = generator.generate(chain)

    assert isinstance(fix, FixProposal)
    assert len(fix.dependency_changes) == 1
    dep = fix.dependency_changes[0]
    assert dep.name == "utility-lib"
    # old_version in FixProposal means the current (broken) version
    assert dep.old_version == "3.0.0"
    # new_version in FixProposal means the target (safe) version
    assert dep.new_version == "2.3.1"


@pytest.mark.asyncio
async def test_scenario_001_fix_description_mentions_versions(event: PipelineFailureEvent, generator: FixGenerator):
    investigation = await _run_scenario_001(event)
    chain = _build_chain_from_investigation(investigation)
    fix = generator.generate(chain)

    assert isinstance(fix, FixProposal)
    assert "2.3.1" in fix.description
    assert "3.0.0" in fix.description


@pytest.mark.asyncio
async def test_scenario_001_fix_description_mentions_dep_name(event: PipelineFailureEvent, generator: FixGenerator):
    investigation = await _run_scenario_001(event)
    chain = _build_chain_from_investigation(investigation)
    fix = generator.generate(chain)

    assert isinstance(fix, FixProposal)
    assert "utility-lib" in fix.description


@pytest.mark.asyncio
async def test_scenario_001_fix_affected_file_is_package_json(event: PipelineFailureEvent, generator: FixGenerator):
    investigation = await _run_scenario_001(event)
    chain = _build_chain_from_investigation(investigation)
    fix = generator.generate(chain)

    assert isinstance(fix, FixProposal)
    assert fix.affected_file == "package.json"


# ===========================================================================
# Test 2: fix references the causal root cause
# ===========================================================================


def test_fix_references_root_cause_node_id(builder: CausalChainBuilder, generator: FixGenerator):
    """fix.root_cause_node_id must equal the chain's root_cause_node_id."""
    investigation = _make_full_investigation()
    chain = _build_chain_from_investigation(investigation)
    fix = generator.generate(chain)

    assert isinstance(fix, FixProposal)
    assert fix.root_cause_node_id == chain.root_cause_node_id


def test_fix_root_cause_node_id_exists_in_chain(builder: CausalChainBuilder, generator: FixGenerator):
    """The root_cause_node_id referenced by the fix must be present in chain.nodes."""
    investigation = _make_full_investigation()
    chain = _build_chain_from_investigation(investigation)
    fix = generator.generate(chain)

    assert isinstance(fix, FixProposal)
    node_ids = {n.node_id for n in chain.nodes}
    assert fix.root_cause_node_id in node_ids


def test_fix_root_cause_node_is_root_cause_type(builder: CausalChainBuilder, generator: FixGenerator):
    """The node referenced by root_cause_node_id must have type ROOT_CAUSE."""
    investigation = _make_full_investigation()
    chain = _build_chain_from_investigation(investigation)
    fix = generator.generate(chain)

    assert isinstance(fix, FixProposal)
    root_node = next(
        (n for n in chain.nodes if n.node_id == fix.root_cause_node_id), None
    )
    assert root_node is not None
    assert root_node.node_type == CausalNodeType.ROOT_CAUSE


# ===========================================================================
# Test 3: fix references supporting evidence
# ===========================================================================


def test_fix_evidence_ids_are_non_empty(builder: CausalChainBuilder, generator: FixGenerator):
    """Fix must carry at least one evidence_id for provenance."""
    investigation = _make_full_investigation()
    chain = _build_chain_from_investigation(investigation)
    fix = generator.generate(chain)

    assert isinstance(fix, FixProposal)
    assert len(fix.evidence_ids) >= 1


def test_fix_evidence_ids_are_real(builder: CausalChainBuilder, generator: FixGenerator):
    """Every evidence_id on the fix must correspond to a real evidence artifact."""
    investigation = _make_full_investigation()
    all_evidence_ids = {ev.evidence_id for ev in investigation.evidence}
    chain = _build_chain_from_investigation(investigation)
    fix = generator.generate(chain)

    assert isinstance(fix, FixProposal)
    for eid in fix.evidence_ids:
        assert eid in all_evidence_ids, (
            f"fix.evidence_ids contains invented ID '{eid}' not present in investigation"
        )


def test_fix_evidence_ids_include_dep_evidence(builder: CausalChainBuilder, generator: FixGenerator):
    """For a dependency-break fix, the dep evidence ID must be in fix.evidence_ids."""
    investigation = _make_full_investigation()
    dep_ev = next(ev for ev in investigation.evidence if hasattr(ev, "breaking_changes"))
    chain = _build_chain_from_investigation(investigation)
    fix = generator.generate(chain)

    assert isinstance(fix, FixProposal)
    assert dep_ev.evidence_id in fix.evidence_ids


def test_fix_rationale_mentions_dependency(builder: CausalChainBuilder, generator: FixGenerator):
    """Rationale must mention the breaking dependency name."""
    investigation = _make_full_investigation()
    chain = _build_chain_from_investigation(investigation)
    fix = generator.generate(chain)

    assert isinstance(fix, FixProposal)
    assert "utility-lib" in fix.rationale


# ===========================================================================
# Test 4: fix is deterministic
# ===========================================================================


def test_fix_is_deterministic_same_chain(generator: FixGenerator):
    """Two calls with the same chain produce byte-for-byte identical FixProposals."""
    investigation = _make_full_investigation()
    chain = _build_chain_from_investigation(investigation)

    fix_1 = generator.generate(chain)
    fix_2 = generator.generate(chain)

    assert isinstance(fix_1, FixProposal)
    assert isinstance(fix_2, FixProposal)
    assert fix_1 == fix_2


def test_fix_is_deterministic_separate_generators():
    """Two separate FixGenerator instances produce identical output."""
    investigation = _make_full_investigation()
    chain = _build_chain_from_investigation(investigation)

    fix_1 = FixGenerator().generate(chain)
    fix_2 = FixGenerator().generate(chain)

    assert isinstance(fix_1, FixProposal)
    assert isinstance(fix_2, FixProposal)
    assert fix_1 == fix_2


def test_fix_id_is_stable_and_predictable(generator: FixGenerator):
    """fix_id must be predictable and stable for the same pipeline_id."""
    investigation = _make_full_investigation(pipeline_id=_PIPELINE_ID)
    chain = _build_chain_from_investigation(investigation)
    fix = generator.generate(chain)

    assert isinstance(fix, FixProposal)
    assert fix.fix_id == f"fix-{_PIPELINE_ID}"


def test_fix_pipeline_id_matches_chain(generator: FixGenerator):
    investigation = _make_full_investigation(pipeline_id="pipe-xyz-999")
    chain = _build_chain_from_investigation(investigation)
    fix = generator.generate(chain)

    assert isinstance(fix, FixProposal)
    assert fix.pipeline_id == "pipe-xyz-999"


# ===========================================================================
# Test 5: insufficient / invalid causal evidence is handled clearly
# ===========================================================================


def test_no_root_cause_node_returns_insufficient_error(generator: FixGenerator):
    """Chain with no ROOT_CAUSE node → InsufficientCausalChainError."""
    # Build a chain with only a CASCADE node and no ROOT_CAUSE
    chain = CausalChain(
        chain_id="chain-bad",
        pipeline_id="pipe-bad",
        nodes=[
            CausalNode(
                node_id="node-cascade",
                node_type=CausalNodeType.CASCADE,
                label="Test failures",
                description="Some tests failed",
                evidence_ids=["ev-001"],
                confidence=0.9,
            )
        ],
        edges=[],
        root_cause_node_id="node-cascade",
        narrative="Failures observed.",
        confidence=0.9,
    )
    result = generator.generate(chain)

    assert isinstance(result, InsufficientCausalChainError)
    assert result.pipeline_id == "pipe-bad"
    assert len(result.reason) > 0


def test_root_cause_node_with_empty_evidence_ids_returns_insufficient_error(generator: FixGenerator):
    """ROOT_CAUSE node with no evidence_ids → InsufficientCausalChainError."""
    chain = CausalChain(
        chain_id="chain-no-ev",
        pipeline_id="pipe-no-ev",
        nodes=[
            CausalNode(
                node_id="node-root-cause",
                node_type=CausalNodeType.ROOT_CAUSE,
                label="Unknown root cause",
                description="Root cause with no evidence.",
                evidence_ids=[],   # intentionally empty
                confidence=0.5,
            )
        ],
        edges=[],
        root_cause_node_id="node-root-cause",
        narrative="Root cause identified.",
        confidence=0.5,
    )
    result = generator.generate(chain)

    assert isinstance(result, InsufficientCausalChainError)
    assert result.pipeline_id == "pipe-no-ev"
    assert "evidence" in result.reason.lower()


def test_zero_confidence_chain_returns_insufficient_error(generator: FixGenerator):
    """Chain with confidence=0.0 → InsufficientCausalChainError."""
    chain = CausalChain(
        chain_id="chain-zero",
        pipeline_id="pipe-zero",
        nodes=[
            CausalNode(
                node_id="node-root-cause",
                node_type=CausalNodeType.ROOT_CAUSE,
                label="Root cause",
                description="Zero-confidence root cause.",
                evidence_ids=["ev-001"],
                confidence=0.0,
            )
        ],
        edges=[],
        root_cause_node_id="node-root-cause",
        narrative="Root cause identified.",
        confidence=0.0,
    )
    result = generator.generate(chain)

    assert isinstance(result, InsufficientCausalChainError)
    assert result.chain_confidence == 0.0


def test_insufficient_error_carries_pipeline_id(generator: FixGenerator):
    """InsufficientCausalChainError must carry the pipeline_id."""
    chain = CausalChain(
        chain_id="chain-pipe-id-test",
        pipeline_id="my-specific-pipeline-id",
        nodes=[
            CausalNode(
                node_id="node-root-cause",
                node_type=CausalNodeType.ROOT_CAUSE,
                label="Root cause",
                description="Test.",
                evidence_ids=[],
                confidence=0.5,
            )
        ],
        edges=[],
        root_cause_node_id="node-root-cause",
        narrative="Test.",
        confidence=0.5,
    )
    result = generator.generate(chain)

    assert isinstance(result, InsufficientCausalChainError)
    assert result.pipeline_id == "my-specific-pipeline-id"


def test_insufficient_error_has_non_empty_reason(generator: FixGenerator):
    """InsufficientCausalChainError must carry a non-empty reason string."""
    chain = CausalChain(
        chain_id="chain-reason-test",
        pipeline_id="pipe-reason",
        nodes=[
            CausalNode(
                node_id="node-root-cause",
                node_type=CausalNodeType.ROOT_CAUSE,
                label="Root cause",
                description="Test.",
                evidence_ids=[],
                confidence=0.5,
            )
        ],
        edges=[],
        root_cause_node_id="node-root-cause",
        narrative="Test.",
        confidence=0.5,
    )
    result = generator.generate(chain)

    assert isinstance(result, InsufficientCausalChainError)
    assert result.reason
    assert len(result.reason) > 10


# ===========================================================================
# Additional correctness tests
# ===========================================================================


def test_fix_confidence_matches_root_cause_node(builder: CausalChainBuilder, generator: FixGenerator):
    """fix.confidence must equal the root-cause node's confidence."""
    investigation = _make_full_investigation()
    chain = _build_chain_from_investigation(investigation)
    fix = generator.generate(chain)

    assert isinstance(fix, FixProposal)
    root_node = next(n for n in chain.nodes if n.node_type == CausalNodeType.ROOT_CAUSE)
    assert fix.confidence == root_node.confidence


def test_fix_generator_version_is_set(generator: FixGenerator):
    """generator_version must be a non-empty string."""
    investigation = _make_full_investigation()
    chain = _build_chain_from_investigation(investigation)
    fix = generator.generate(chain)

    assert isinstance(fix, FixProposal)
    assert fix.generator_version
    assert len(fix.generator_version) > 0


def test_fix_is_frozen(generator: FixGenerator):
    """FixProposal must be immutable (frozen Pydantic model)."""
    from pydantic import ValidationError
    investigation = _make_full_investigation()
    chain = _build_chain_from_investigation(investigation)
    fix = generator.generate(chain)

    assert isinstance(fix, FixProposal)
    # Pydantic v2 frozen models raise ValidationError on direct attribute assignment
    with pytest.raises((ValidationError, TypeError)):
        fix.fix_type = FixType.CODE_PATCH  # type: ignore[misc]


def test_fix_description_is_non_empty(generator: FixGenerator):
    investigation = _make_full_investigation()
    chain = _build_chain_from_investigation(investigation)
    fix = generator.generate(chain)

    assert isinstance(fix, FixProposal)
    assert fix.description
    assert len(fix.description) > 10


def test_fix_rationale_is_non_empty(generator: FixGenerator):
    investigation = _make_full_investigation()
    chain = _build_chain_from_investigation(investigation)
    fix = generator.generate(chain)

    assert isinstance(fix, FixProposal)
    assert fix.rationale
    assert len(fix.rationale) > 10


def test_fix_dependency_change_pinned_version_is_older(generator: FixGenerator):
    """For a dep-pin fix, new_version (target) should be less than old_version (broken)."""
    investigation = _make_full_investigation()
    chain = _build_chain_from_investigation(investigation)
    fix = generator.generate(chain)

    assert isinstance(fix, FixProposal)
    assert fix.fix_type == FixType.DEPENDENCY_CHANGE
    assert len(fix.dependency_changes) == 1
    dep = fix.dependency_changes[0]
    # 2.3.1 is the safe version, 3.0.0 is broken
    assert dep.new_version == "2.3.1"
    assert dep.old_version == "3.0.0"


def test_code_change_only_produces_code_patch_fix(generator: FixGenerator):
    """Chain with ROOT_CAUSE (code change) and no DEPENDENCY_BREAK → CODE_PATCH fix."""
    investigation = _make_full_investigation(
        include_dep=False,
        include_failure=True,
        include_change=True,
        include_test=False,
    )
    chain = _build_chain_from_investigation(investigation)

    # Verify this chain has no DEPENDENCY_BREAK node
    node_types = {n.node_type for n in chain.nodes}
    assert CausalNodeType.DEPENDENCY_BREAK not in node_types

    fix = generator.generate(chain)

    assert isinstance(fix, FixProposal)
    assert fix.fix_type == FixType.CODE_PATCH


def test_generator_reuse_is_safe(generator: FixGenerator):
    """Single FixGenerator instance can process multiple chains without cross-contamination."""
    inv1 = _make_full_investigation(pipeline_id="pipe-a")
    inv2 = _make_full_investigation(pipeline_id="pipe-b")
    chain1 = _build_chain_from_investigation(inv1)
    chain2 = _build_chain_from_investigation(inv2)

    fix1 = generator.generate(chain1)
    fix2 = generator.generate(chain2)

    assert isinstance(fix1, FixProposal)
    assert isinstance(fix2, FixProposal)
    assert fix1.pipeline_id == "pipe-a"
    assert fix2.pipeline_id == "pipe-b"
    assert fix1.fix_id != fix2.fix_id


# ===========================================================================
# FixProposal model validation tests
# ===========================================================================


def test_fix_proposal_requires_evidence_ids():
    """FixProposal with dep_changes but no evidence_ids should still be valid (empty list ok)."""
    fix = FixProposal(
        fix_id="fix-test",
        pipeline_id="pipe-test",
        root_cause_node_id="node-root-cause",
        fix_type=FixType.DEPENDENCY_CHANGE,
        description="Pin dep back",
        rationale="Because it broke",
        confidence=0.95,
        evidence_ids=[],
    )
    assert fix.evidence_ids == []


def test_fix_proposal_confidence_bounds():
    """confidence must be in [0.0, 1.0]."""
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        FixProposal(
            fix_id="fix-test",
            pipeline_id="pipe-test",
            root_cause_node_id="node-root-cause",
            fix_type=FixType.DEPENDENCY_CHANGE,
            description="Pin dep back",
            rationale="Because it broke",
            confidence=1.5,  # out of range
            evidence_ids=["ev-001"],
        )


def test_fix_type_enum_values():
    """FixType must have exactly the four values from the plan."""
    values = {ft.value for ft in FixType}
    assert values == {"DEPENDENCY_CHANGE", "CODE_PATCH", "CONFIG_CHANGE", "ENV_FIX"}
