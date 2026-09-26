"""
Unit tests for BobOrchestrator + InvestigationResult (Task 6).

Coverage
--------
Orchestrator:
- initializes all six investigators
- runs all six investigators
- uses the correct scenario_id
- publishes all successful evidence to the bus
- returns InvestigationResult with COMPLETE status when all succeed
- evidence list contains all six artifacts
- outcomes list has one entry per investigator
- handles a single investigator failure (PARTIAL status)
- handles all investigators failing (FAILED status)
- preserves evidence from successful investigators when one fails
- errors dict populated correctly on failure
- failed investigator outcomes recorded correctly
- provider ValueError propagates to errors dict
- unsupported scenario handled correctly
- deterministic: repeated runs produce consistent evidence types
- pipeline_id and scenario_id are correctly threaded through

InvestigationResult:
- COMPLETE when all succeed
- PARTIAL when some fail
- FAILED when all fail
- evidence sorted by created_at if multiple
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from app.agents.orchestrator import BobOrchestrator, _INVESTIGATOR_CLASSES
from app.ai.mock_provider import MockProvider
from app.ai.provider import AIProvider
from app.models.events import PipelineFailureEvent
from app.models.evidence import (
    BaseEvidence,
    EvidenceType,
    EvidenceSource,
    FailureEvidence,
)
from app.models.investigation import InvestigationResult, InvestigationStatus


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

_SCENARIO_ID = "scenario-001"


@pytest.fixture
def event() -> PipelineFailureEvent:
    return PipelineFailureEvent(
        id="evt-test-001",
        repo="acme/payments-service",
        branch="feature/update-deps",
        commit_sha="a1b2c3d4",
        pipeline_run_id="run-test-001",
        timestamp=datetime(2024, 3, 15, 14, 32, 0, tzinfo=timezone.utc),
        failure_stage="test",
    )


@pytest.fixture
def mock_provider() -> MockProvider:
    return MockProvider()


@pytest.fixture
def orchestrator(mock_provider: MockProvider) -> BobOrchestrator:
    return BobOrchestrator(provider=mock_provider)


# ---------------------------------------------------------------------------
# Helper: failing provider stub
# ---------------------------------------------------------------------------


class _AlwaysFailProvider(AIProvider):
    """Provider that always raises ValueError for any query."""

    async def query(self, scenario_id: str, prompt_key: str) -> dict[str, Any]:
        raise ValueError(f"Injected failure for {prompt_key}")


class _PartialFailProvider(AIProvider):
    """
    Provider that fails for one specific prompt_key, succeeds for all others.
    """

    def __init__(self, failing_key: str) -> None:
        self._failing_key = failing_key
        self._real = MockProvider()

    async def query(self, scenario_id: str, prompt_key: str) -> dict[str, Any]:
        if prompt_key == self._failing_key:
            raise ValueError(f"Injected failure for {prompt_key}")
        return await self._real.query(scenario_id, prompt_key)


# ---------------------------------------------------------------------------
# INVESTIGATOR_CLASSES sanity
# ---------------------------------------------------------------------------


def test_investigator_classes_contains_six():
    assert len(_INVESTIGATOR_CLASSES) == 6


def test_all_investigator_classes_have_agent_id():
    for cls in _INVESTIGATOR_CLASSES:
        assert hasattr(cls, "agent_id"), f"{cls.__name__} missing agent_id"
        assert isinstance(cls.agent_id, str)


def test_all_investigator_classes_have_prompt_key():
    for cls in _INVESTIGATOR_CLASSES:
        assert hasattr(cls, "PROMPT_KEY"), f"{cls.__name__} missing PROMPT_KEY"


# ---------------------------------------------------------------------------
# Happy path — all six succeed
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_returns_investigation_result(orchestrator, event):
    result = await orchestrator.run(event, _SCENARIO_ID)
    assert isinstance(result, InvestigationResult)


@pytest.mark.asyncio
async def test_run_all_succeed_status_is_complete(orchestrator, event):
    result = await orchestrator.run(event, _SCENARIO_ID)
    assert result.status == InvestigationStatus.COMPLETE


@pytest.mark.asyncio
async def test_run_collects_six_evidence_artifacts(orchestrator, event):
    result = await orchestrator.run(event, _SCENARIO_ID)
    assert len(result.evidence) == 6


@pytest.mark.asyncio
async def test_run_has_six_outcomes(orchestrator, event):
    result = await orchestrator.run(event, _SCENARIO_ID)
    assert len(result.outcomes) == 6


@pytest.mark.asyncio
async def test_run_all_outcomes_are_successful(orchestrator, event):
    result = await orchestrator.run(event, _SCENARIO_ID)
    for outcome in result.outcomes:
        assert outcome.success is True
        assert outcome.error is None
        assert outcome.evidence_id is not None


@pytest.mark.asyncio
async def test_run_errors_dict_is_empty_on_success(orchestrator, event):
    result = await orchestrator.run(event, _SCENARIO_ID)
    assert result.errors == {}


@pytest.mark.asyncio
async def test_run_pipeline_id_matches_event(orchestrator, event):
    result = await orchestrator.run(event, _SCENARIO_ID)
    assert result.pipeline_id == event.pipeline_run_id


@pytest.mark.asyncio
async def test_run_scenario_id_is_preserved(orchestrator, event):
    result = await orchestrator.run(event, _SCENARIO_ID)
    assert result.scenario_id == _SCENARIO_ID


@pytest.mark.asyncio
async def test_run_has_timing_fields(orchestrator, event):
    result = await orchestrator.run(event, _SCENARIO_ID)
    assert result.started_at is not None
    assert result.completed_at is not None
    assert result.completed_at >= result.started_at


# ---------------------------------------------------------------------------
# Evidence type coverage
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_collects_all_six_evidence_types(orchestrator, event):
    result = await orchestrator.run(event, _SCENARIO_ID)
    types_found = {ev.evidence_type for ev in result.evidence}
    assert types_found == {
        EvidenceType.FAILURE,
        EvidenceType.CHANGE,
        EvidenceType.DEPENDENCY,
        EvidenceType.TEST,
        EvidenceType.INFRA,
        EvidenceType.HISTORICAL,
    }


@pytest.mark.asyncio
async def test_run_all_evidence_pipeline_ids_match(orchestrator, event):
    result = await orchestrator.run(event, _SCENARIO_ID)
    for ev in result.evidence:
        assert ev.pipeline_id == event.pipeline_run_id


@pytest.mark.asyncio
async def test_run_evidence_ids_are_all_distinct(orchestrator, event):
    result = await orchestrator.run(event, _SCENARIO_ID)
    ids = [ev.evidence_id for ev in result.evidence]
    assert len(ids) == len(set(ids)), "Evidence IDs must be unique"


@pytest.mark.asyncio
async def test_run_outcome_agent_ids_match_investigator_agent_ids(orchestrator, event):
    result = await orchestrator.run(event, _SCENARIO_ID)
    expected_agent_ids = {cls.agent_id for cls in _INVESTIGATOR_CLASSES}
    result_agent_ids = {o.agent_id for o in result.outcomes}
    assert result_agent_ids == expected_agent_ids


@pytest.mark.asyncio
async def test_outcome_evidence_ids_match_evidence_in_bus(orchestrator, event):
    result = await orchestrator.run(event, _SCENARIO_ID)
    bus_ids = {ev.evidence_id for ev in result.evidence}
    outcome_ids = {o.evidence_id for o in result.outcomes if o.evidence_id}
    assert outcome_ids == bus_ids


# ---------------------------------------------------------------------------
# Determinism — same provider produces consistent results
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_is_deterministic_for_scenario(event):
    """Two runs with MockProvider must produce the same evidence type set."""
    orc = BobOrchestrator(provider=MockProvider())
    r1 = await orc.run(event, _SCENARIO_ID)
    r2 = await orc.run(event, _SCENARIO_ID)
    assert {ev.evidence_type for ev in r1.evidence} == {
        ev.evidence_type for ev in r2.evidence
    }


@pytest.mark.asyncio
async def test_run_repeated_calls_do_not_accumulate(event):
    """Second run must return exactly 6 artifacts, not 12."""
    orc = BobOrchestrator(provider=MockProvider())
    await orc.run(event, _SCENARIO_ID)
    r2 = await orc.run(event, _SCENARIO_ID)
    assert len(r2.evidence) == 6


# ---------------------------------------------------------------------------
# Single investigator failure → PARTIAL
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_single_failure_status_is_partial(event):
    provider = _PartialFailProvider(failing_key="log_investigator")
    orc = BobOrchestrator(provider=provider)
    result = await orc.run(event, _SCENARIO_ID)
    assert result.status == InvestigationStatus.PARTIAL


@pytest.mark.asyncio
async def test_single_failure_five_evidence_artifacts(event):
    provider = _PartialFailProvider(failing_key="log_investigator")
    orc = BobOrchestrator(provider=provider)
    result = await orc.run(event, _SCENARIO_ID)
    assert len(result.evidence) == 5


@pytest.mark.asyncio
async def test_single_failure_recorded_in_errors(event):
    provider = _PartialFailProvider(failing_key="log_investigator")
    orc = BobOrchestrator(provider=provider)
    result = await orc.run(event, _SCENARIO_ID)
    assert "log_investigator" in result.errors
    assert len(result.errors) == 1


@pytest.mark.asyncio
async def test_single_failure_outcome_marked_as_failed(event):
    provider = _PartialFailProvider(failing_key="log_investigator")
    orc = BobOrchestrator(provider=provider)
    result = await orc.run(event, _SCENARIO_ID)

    failed_outcomes = [o for o in result.outcomes if not o.success]
    assert len(failed_outcomes) == 1
    assert failed_outcomes[0].agent_id == "log_investigator"
    assert failed_outcomes[0].error is not None
    assert failed_outcomes[0].evidence_id is None


@pytest.mark.asyncio
async def test_single_failure_other_evidence_still_present(event):
    """Failing one investigator must not discard the other five artifacts."""
    provider = _PartialFailProvider(failing_key="log_investigator")
    orc = BobOrchestrator(provider=provider)
    result = await orc.run(event, _SCENARIO_ID)

    # FAILURE type from log_investigator should be absent
    types_found = {ev.evidence_type for ev in result.evidence}
    assert EvidenceType.FAILURE not in types_found
    # The other five types should be present
    assert EvidenceType.CHANGE in types_found
    assert EvidenceType.DEPENDENCY in types_found
    assert EvidenceType.TEST in types_found
    assert EvidenceType.INFRA in types_found
    assert EvidenceType.HISTORICAL in types_found


# ---------------------------------------------------------------------------
# Multiple investigator failures → PARTIAL / FAILED
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_multiple_failures_partial_when_some_succeed(event):
    class _TwoFailProvider(AIProvider):
        def __init__(self) -> None:
            self._real = MockProvider()

        async def query(self, scenario_id: str, prompt_key: str) -> dict[str, Any]:
            if prompt_key in ("log_investigator", "code_investigator"):
                raise ValueError(f"Injected failure for {prompt_key}")
            return await self._real.query(scenario_id, prompt_key)

    orc = BobOrchestrator(provider=_TwoFailProvider())
    result = await orc.run(event, _SCENARIO_ID)

    assert result.status == InvestigationStatus.PARTIAL
    assert len(result.errors) == 2
    assert len(result.evidence) == 4


@pytest.mark.asyncio
async def test_all_failures_status_is_failed(event):
    orc = BobOrchestrator(provider=_AlwaysFailProvider())
    result = await orc.run(event, _SCENARIO_ID)
    assert result.status == InvestigationStatus.FAILED


@pytest.mark.asyncio
async def test_all_failures_evidence_is_empty(event):
    orc = BobOrchestrator(provider=_AlwaysFailProvider())
    result = await orc.run(event, _SCENARIO_ID)
    assert result.evidence == []


@pytest.mark.asyncio
async def test_all_failures_errors_has_six_entries(event):
    orc = BobOrchestrator(provider=_AlwaysFailProvider())
    result = await orc.run(event, _SCENARIO_ID)
    assert len(result.errors) == 6


@pytest.mark.asyncio
async def test_all_failures_outcomes_all_marked_failed(event):
    orc = BobOrchestrator(provider=_AlwaysFailProvider())
    result = await orc.run(event, _SCENARIO_ID)
    for outcome in result.outcomes:
        assert outcome.success is False
        assert outcome.error is not None


# ---------------------------------------------------------------------------
# Unsupported scenario propagates error
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_unsupported_scenario_all_fail(event):
    """An unsupported scenario_id causes MockProvider to raise for every key."""
    orc = BobOrchestrator(provider=MockProvider())
    result = await orc.run(event, scenario_id="scenario-999")
    assert result.status == InvestigationStatus.FAILED
    assert len(result.errors) == 6
    assert result.evidence == []


@pytest.mark.asyncio
async def test_unsupported_scenario_error_messages_mention_scenario(event):
    orc = BobOrchestrator(provider=MockProvider())
    result = await orc.run(event, scenario_id="scenario-999")
    for msg in result.errors.values():
        assert "scenario-999" in msg


# ---------------------------------------------------------------------------
# InvestigationResult model fields
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_result_started_at_is_before_completed_at(orchestrator, event):
    result = await orchestrator.run(event, _SCENARIO_ID)
    assert result.started_at <= result.completed_at


@pytest.mark.asyncio
async def test_result_status_enum_values():
    assert InvestigationStatus.COMPLETE == "complete"
    assert InvestigationStatus.PARTIAL == "partial"
    assert InvestigationStatus.FAILED == "failed"
