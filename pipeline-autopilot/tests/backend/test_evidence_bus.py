"""
Unit tests for EvidenceBus (Task 6).

Coverage
--------
- publish evidence
- collect evidence
- preserve evidence identity (evidence_id)
- preserve provenance (source.agent_id)
- preserve evidence type (evidence_type)
- multiple evidence artifacts (all six types)
- empty bus behavior
- collect returns a copy (bus isolation)
- clear resets the bus
- concurrent publish does not lose artifacts
- len() helper
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import pytest

from app.bus.evidence_bus import EvidenceBus
from app.models.evidence import (
    ChangeEvidence,
    DependencyEvidence,
    EvidenceSource,
    EvidenceType,
    FailureEvidence,
    HistoricalEvidence,
    InfraEvidence,
    Severity,
    TestRunEvidence,
)


# ---------------------------------------------------------------------------
# Fixtures — minimal valid evidence builders
# ---------------------------------------------------------------------------


def _source(agent_id: str = "test_agent") -> EvidenceSource:
    return EvidenceSource(agent_id=agent_id, extraction_method="mock")


def _failure_evidence(
    evidence_id: str = "ev-001",
    pipeline_id: str = "pipe-1",
    agent_id: str = "log_investigator",
) -> FailureEvidence:
    return FailureEvidence(
        evidence_id=evidence_id,
        pipeline_id=pipeline_id,
        source=_source(agent_id),
        summary="Test failure",
        confidence=0.9,
        error_class="TypeError",
        error_message="something broke",
        affected_stage="test",
    )


def _change_evidence(
    evidence_id: str = "ev-002",
    pipeline_id: str = "pipe-1",
) -> ChangeEvidence:
    return ChangeEvidence(
        evidence_id=evidence_id,
        pipeline_id=pipeline_id,
        source=_source("code_investigator"),
        summary="Test change",
        confidence=0.8,
        commit_sha="abc123",
    )


# ---------------------------------------------------------------------------
# Empty bus
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_empty_bus_collect_returns_empty_list():
    bus = EvidenceBus()
    assert bus.collect() == []


@pytest.mark.asyncio
async def test_empty_bus_len_is_zero():
    bus = EvidenceBus()
    assert len(bus) == 0


# ---------------------------------------------------------------------------
# publish → collect round-trip
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_publish_single_artifact():
    bus = EvidenceBus()
    ev = _failure_evidence()
    await bus.publish(ev)
    collected = bus.collect()
    assert len(collected) == 1
    assert collected[0] is ev


@pytest.mark.asyncio
async def test_publish_multiple_artifacts():
    bus = EvidenceBus()
    ev1 = _failure_evidence(evidence_id="ev-001")
    ev2 = _change_evidence(evidence_id="ev-002")
    await bus.publish(ev1)
    await bus.publish(ev2)
    collected = bus.collect()
    assert len(collected) == 2


@pytest.mark.asyncio
async def test_len_matches_publish_count():
    bus = EvidenceBus()
    await bus.publish(_failure_evidence(evidence_id="ev-001"))
    await bus.publish(_change_evidence(evidence_id="ev-002"))
    assert len(bus) == 2


# ---------------------------------------------------------------------------
# Identity preservation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_evidence_id_is_preserved():
    bus = EvidenceBus()
    ev = _failure_evidence(evidence_id="ev-unique-id")
    await bus.publish(ev)
    assert bus.collect()[0].evidence_id == "ev-unique-id"


@pytest.mark.asyncio
async def test_provenance_is_preserved():
    bus = EvidenceBus()
    ev = _failure_evidence(agent_id="log_investigator")
    await bus.publish(ev)
    assert bus.collect()[0].source.agent_id == "log_investigator"


@pytest.mark.asyncio
async def test_evidence_type_is_preserved():
    bus = EvidenceBus()
    ev = _failure_evidence()
    await bus.publish(ev)
    assert bus.collect()[0].evidence_type == EvidenceType.FAILURE


@pytest.mark.asyncio
async def test_pipeline_id_is_preserved():
    bus = EvidenceBus()
    ev = _failure_evidence(pipeline_id="run-xyz-999")
    await bus.publish(ev)
    assert bus.collect()[0].pipeline_id == "run-xyz-999"


# ---------------------------------------------------------------------------
# All six evidence types can be stored
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_all_six_evidence_types_can_be_published():
    from app.models.evidence import (
        DepChange,
        DependencyEvidence,
        FailedTest,
        HistoricalEvidence,
        InfraEvidence,
        SimilarFailure,
    )

    bus = EvidenceBus()

    failure = _failure_evidence(evidence_id="ev-f")
    change = _change_evidence(evidence_id="ev-c")
    dep = DependencyEvidence(
        evidence_id="ev-d",
        pipeline_id="pipe-1",
        source=_source("dependency_investigator"),
        summary="dep evidence",
        confidence=0.9,
    )
    test_run = TestRunEvidence(
        evidence_id="ev-t",
        pipeline_id="pipe-1",
        source=_source("test_investigator"),
        summary="test evidence",
        confidence=0.9,
        total_run=10,
        total_failed=2,
        total_passed=8,
    )
    infra = InfraEvidence(
        evidence_id="ev-i",
        pipeline_id="pipe-1",
        source=_source("infra_investigator"),
        summary="infra evidence",
        confidence=0.9,
    )
    hist = HistoricalEvidence(
        evidence_id="ev-h",
        pipeline_id="pipe-1",
        source=_source("history_investigator"),
        summary="historical evidence",
        confidence=0.9,
    )

    for ev in [failure, change, dep, test_run, infra, hist]:
        await bus.publish(ev)

    collected = bus.collect()
    assert len(collected) == 6

    types_found = {ev.evidence_type for ev in collected}
    assert types_found == {
        EvidenceType.FAILURE,
        EvidenceType.CHANGE,
        EvidenceType.DEPENDENCY,
        EvidenceType.TEST,
        EvidenceType.INFRA,
        EvidenceType.HISTORICAL,
    }


# ---------------------------------------------------------------------------
# collect returns an independent copy
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_collect_returns_copy():
    """Mutating the returned list must not affect the bus."""
    bus = EvidenceBus()
    ev = _failure_evidence()
    await bus.publish(ev)

    first = bus.collect()
    first.clear()

    second = bus.collect()
    assert len(second) == 1  # bus still has one artifact


# ---------------------------------------------------------------------------
# clear resets state
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_clear_empties_bus():
    bus = EvidenceBus()
    await bus.publish(_failure_evidence())
    bus.clear()
    assert bus.collect() == []
    assert len(bus) == 0


@pytest.mark.asyncio
async def test_publish_after_clear():
    bus = EvidenceBus()
    ev1 = _failure_evidence(evidence_id="ev-001")
    await bus.publish(ev1)
    bus.clear()

    ev2 = _change_evidence(evidence_id="ev-002")
    await bus.publish(ev2)

    collected = bus.collect()
    assert len(collected) == 1
    assert collected[0].evidence_id == "ev-002"


# ---------------------------------------------------------------------------
# Concurrent publish safety
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_concurrent_publish_collects_all():
    """
    Publish 10 artifacts concurrently — the bus must collect all 10.

    This tests that the asyncio.Lock inside publish() prevents data loss
    when multiple coroutines write simultaneously.
    """
    bus = EvidenceBus()

    async def _publish_one(i: int) -> None:
        ev = _failure_evidence(evidence_id=f"ev-{i:03d}", pipeline_id=f"pipe-{i}")
        await bus.publish(ev)

    await asyncio.gather(*[_publish_one(i) for i in range(10)])

    collected = bus.collect()
    assert len(collected) == 10

    ids = {ev.evidence_id for ev in collected}
    assert len(ids) == 10  # no duplicates, no losses


# ---------------------------------------------------------------------------
# Insertion order is preserved for sequential publishes
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sequential_publish_preserves_insertion_order():
    bus = EvidenceBus()
    ev1 = _failure_evidence(evidence_id="ev-first")
    ev2 = _change_evidence(evidence_id="ev-second")

    await bus.publish(ev1)
    await bus.publish(ev2)

    collected = bus.collect()
    assert collected[0].evidence_id == "ev-first"
    assert collected[1].evidence_id == "ev-second"
