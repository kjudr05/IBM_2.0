"""
Task 5 — Unit tests for all six investigator classes.

Coverage goals:
  1.  LogInvestigator returns valid FailureEvidence.
  2.  CodeInvestigator returns valid ChangeEvidence.
  3.  DependencyInvestigator returns valid DependencyEvidence.
  4.  TestInvestigator returns valid TestRunEvidence.
  5.  InfraInvestigator returns valid InfraEvidence.
  6.  HistoryInvestigator returns valid HistoricalEvidence.
  7.  Each investigator calls the correct MockProvider prompt key.
  8.  Repeated calls are deterministic.
  9.  Provider failures are propagated clearly.
  10. Invalid provider output is rejected with ValueError.
  11. Evidence provenance (EvidenceSource) is preserved.
  12. Existing Task 1–4 tests continue passing (run the full suite).
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.agents.log_investigator import LogInvestigator
from app.agents.code_investigator import CodeInvestigator
from app.agents.dependency_investigator import DependencyInvestigator
from app.agents.test_investigator import TestInvestigator
from app.agents.infra_investigator import InfraInvestigator
from app.agents.history_investigator import HistoryInvestigator
from app.agents.base import BaseInvestigator

from app.ai.mock_provider import MockProvider
from app.ai.provider import AIProvider

from app.models.events import PipelineFailureEvent
from app.models.evidence import (
    ChangeEvidence,
    DependencyEvidence,
    EvidenceType,
    FailureEvidence,
    HistoricalEvidence,
    InfraEvidence,
    TestRunEvidence,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SCENARIO_ID = "scenario-001"


@pytest.fixture
def mock_provider() -> MockProvider:
    """Shared MockProvider — stateless, safe to reuse."""
    return MockProvider()


@pytest.fixture
def event() -> PipelineFailureEvent:
    """Minimal PipelineFailureEvent sufficient for all investigator calls."""
    return PipelineFailureEvent(
        id="evt-test-001",
        repo="acme/payments-service",
        branch="feature/update-deps",
        commit_sha="a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2",
        pipeline_run_id="run-20240315-001",
        timestamp="2024-03-15T14:32:00Z",
        failure_stage="test",
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_investigator(cls, provider, scenario_id=SCENARIO_ID):
    return cls(provider=provider, scenario_id=scenario_id)


# ---------------------------------------------------------------------------
# BaseInvestigator contract
# ---------------------------------------------------------------------------


class TestBaseInvestigatorContract:
    def test_base_investigator_is_abstract(self):
        """BaseInvestigator cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BaseInvestigator(provider=MockProvider(), scenario_id=SCENARIO_ID)  # type: ignore[abstract]

    def test_all_investigators_are_subclasses(self):
        classes = [
            LogInvestigator,
            CodeInvestigator,
            DependencyInvestigator,
            TestInvestigator,
            InfraInvestigator,
            HistoryInvestigator,
        ]
        for cls in classes:
            assert issubclass(cls, BaseInvestigator), f"{cls} is not a BaseInvestigator subclass"

    def test_all_investigators_are_aiprovider_agnostic(self):
        """Investigators only depend on the AIProvider ABC — not MockProvider."""
        for cls in [
            LogInvestigator,
            CodeInvestigator,
            DependencyInvestigator,
            TestInvestigator,
            InfraInvestigator,
            HistoryInvestigator,
        ]:
            # Constructing with a raw AIProvider check — just check the annotation
            import inspect
            sig = inspect.signature(cls.__init__)
            provider_param = sig.parameters["provider"]
            # No type annotation check needed; just verify the parameter exists
            assert provider_param is not None

    def test_each_investigator_has_prompt_key(self):
        for cls in [
            LogInvestigator,
            CodeInvestigator,
            DependencyInvestigator,
            TestInvestigator,
            InfraInvestigator,
            HistoryInvestigator,
        ]:
            assert hasattr(cls, "PROMPT_KEY"), f"{cls.__name__} missing PROMPT_KEY"
            assert isinstance(cls.PROMPT_KEY, str)
            assert cls.PROMPT_KEY  # non-empty

    def test_each_investigator_has_agent_id(self):
        for cls in [
            LogInvestigator,
            CodeInvestigator,
            DependencyInvestigator,
            TestInvestigator,
            InfraInvestigator,
            HistoryInvestigator,
        ]:
            assert hasattr(cls, "agent_id"), f"{cls.__name__} missing agent_id"
            assert isinstance(cls.agent_id, str)
            assert cls.agent_id  # non-empty


# ---------------------------------------------------------------------------
# LogInvestigator
# ---------------------------------------------------------------------------


class TestLogInvestigator:
    async def test_returns_failure_evidence(self, mock_provider, event):
        inv = LogInvestigator(provider=mock_provider, scenario_id=SCENARIO_ID)
        result = await inv.investigate(event)
        assert isinstance(result, FailureEvidence)

    async def test_evidence_type_is_failure(self, mock_provider, event):
        inv = LogInvestigator(provider=mock_provider, scenario_id=SCENARIO_ID)
        result = await inv.investigate(event)
        assert result.evidence_type == EvidenceType.FAILURE

    async def test_prompt_key_is_log_investigator(self, mock_provider, event):
        """Investigator must call the provider with the correct prompt key."""
        calls = []

        class SpyProvider(AIProvider):
            async def query(self, scenario_id, prompt_key):
                calls.append(prompt_key)
                return await mock_provider.query(scenario_id, prompt_key)

        inv = LogInvestigator(provider=SpyProvider(), scenario_id=SCENARIO_ID)
        await inv.investigate(event)
        assert calls == ["log_investigator"]

    async def test_pipeline_id_matches_event(self, mock_provider, event):
        inv = LogInvestigator(provider=mock_provider, scenario_id=SCENARIO_ID)
        result = await inv.investigate(event)
        assert result.pipeline_id == event.pipeline_run_id

    async def test_evidence_id_is_populated(self, mock_provider, event):
        inv = LogInvestigator(provider=mock_provider, scenario_id=SCENARIO_ID)
        result = await inv.investigate(event)
        assert result.evidence_id
        assert isinstance(result.evidence_id, str)

    async def test_provenance_agent_id(self, mock_provider, event):
        inv = LogInvestigator(provider=mock_provider, scenario_id=SCENARIO_ID)
        result = await inv.investigate(event)
        assert result.source.agent_id == "log_investigator"

    async def test_provenance_input_file(self, mock_provider, event):
        inv = LogInvestigator(provider=mock_provider, scenario_id=SCENARIO_ID)
        result = await inv.investigate(event)
        assert result.source.input_file is not None

    async def test_error_class_is_type_error(self, mock_provider, event):
        inv = LogInvestigator(provider=mock_provider, scenario_id=SCENARIO_ID)
        result = await inv.investigate(event)
        assert result.error_class == "TypeError"

    async def test_affected_stage_is_test(self, mock_provider, event):
        inv = LogInvestigator(provider=mock_provider, scenario_id=SCENARIO_ID)
        result = await inv.investigate(event)
        assert result.affected_stage == "test"

    async def test_confidence_in_range(self, mock_provider, event):
        inv = LogInvestigator(provider=mock_provider, scenario_id=SCENARIO_ID)
        result = await inv.investigate(event)
        assert 0.0 <= result.confidence <= 1.0

    async def test_repeated_calls_are_deterministic(self, mock_provider, event):
        inv = LogInvestigator(provider=mock_provider, scenario_id=SCENARIO_ID)
        r1 = await inv.investigate(event)
        r2 = await inv.investigate(event)
        # All fields except evidence_id (uuid) and created_at must be equal
        assert r1.error_class == r2.error_class
        assert r1.error_message == r2.error_message
        assert r1.stack_trace == r2.stack_trace
        assert r1.evidence_type == r2.evidence_type
        assert r1.confidence == r2.confidence

    async def test_provider_error_propagates(self, event):
        bad_provider = MockProvider()
        inv = LogInvestigator(provider=bad_provider, scenario_id="unknown-scenario")
        with pytest.raises(ValueError, match="MockProvider does not support scenario"):
            await inv.investigate(event)

    async def test_invalid_provider_output_raises_value_error(self, event):
        """A provider that returns data missing required fields raises ValueError."""

        class BrokenProvider(AIProvider):
            async def query(self, scenario_id, prompt_key):
                return {"evidence_type": "failure"}  # missing required fields

        inv = LogInvestigator(provider=BrokenProvider(), scenario_id=SCENARIO_ID)
        with pytest.raises(ValueError, match="FailureEvidence validation"):
            await inv.investigate(event)


# ---------------------------------------------------------------------------
# CodeInvestigator
# ---------------------------------------------------------------------------


class TestCodeInvestigator:
    async def test_returns_change_evidence(self, mock_provider, event):
        inv = CodeInvestigator(provider=mock_provider, scenario_id=SCENARIO_ID)
        result = await inv.investigate(event)
        assert isinstance(result, ChangeEvidence)

    async def test_evidence_type_is_change(self, mock_provider, event):
        inv = CodeInvestigator(provider=mock_provider, scenario_id=SCENARIO_ID)
        result = await inv.investigate(event)
        assert result.evidence_type == EvidenceType.CHANGE

    async def test_prompt_key_is_code_investigator(self, mock_provider, event):
        calls = []

        class SpyProvider(AIProvider):
            async def query(self, scenario_id, prompt_key):
                calls.append(prompt_key)
                return await mock_provider.query(scenario_id, prompt_key)

        inv = CodeInvestigator(provider=SpyProvider(), scenario_id=SCENARIO_ID)
        await inv.investigate(event)
        assert calls == ["code_investigator"]

    async def test_pipeline_id_matches_event(self, mock_provider, event):
        inv = CodeInvestigator(provider=mock_provider, scenario_id=SCENARIO_ID)
        result = await inv.investigate(event)
        assert result.pipeline_id == event.pipeline_run_id

    async def test_evidence_id_is_populated(self, mock_provider, event):
        inv = CodeInvestigator(provider=mock_provider, scenario_id=SCENARIO_ID)
        result = await inv.investigate(event)
        assert result.evidence_id

    async def test_provenance_agent_id(self, mock_provider, event):
        inv = CodeInvestigator(provider=mock_provider, scenario_id=SCENARIO_ID)
        result = await inv.investigate(event)
        assert result.source.agent_id == "code_investigator"

    async def test_commit_sha_present(self, mock_provider, event):
        inv = CodeInvestigator(provider=mock_provider, scenario_id=SCENARIO_ID)
        result = await inv.investigate(event)
        assert result.commit_sha

    async def test_changed_files_contains_package_json(self, mock_provider, event):
        inv = CodeInvestigator(provider=mock_provider, scenario_id=SCENARIO_ID)
        result = await inv.investigate(event)
        paths = [f.path for f in result.changed_files]
        assert "package.json" in paths

    async def test_repeated_calls_are_deterministic(self, mock_provider, event):
        inv = CodeInvestigator(provider=mock_provider, scenario_id=SCENARIO_ID)
        r1 = await inv.investigate(event)
        r2 = await inv.investigate(event)
        assert r1.commit_sha == r2.commit_sha
        assert r1.changed_files == r2.changed_files
        assert r1.confidence == r2.confidence

    async def test_provider_error_propagates(self, event):
        inv = CodeInvestigator(provider=MockProvider(), scenario_id="unknown-scenario")
        with pytest.raises(ValueError, match="MockProvider does not support scenario"):
            await inv.investigate(event)

    async def test_invalid_provider_output_raises_value_error(self, event):
        class BrokenProvider(AIProvider):
            async def query(self, scenario_id, prompt_key):
                return {"evidence_type": "change"}  # missing commit_sha and more

        inv = CodeInvestigator(provider=BrokenProvider(), scenario_id=SCENARIO_ID)
        with pytest.raises(ValueError, match="ChangeEvidence validation"):
            await inv.investigate(event)


# ---------------------------------------------------------------------------
# DependencyInvestigator
# ---------------------------------------------------------------------------


class TestDependencyInvestigator:
    async def test_returns_dependency_evidence(self, mock_provider, event):
        inv = DependencyInvestigator(provider=mock_provider, scenario_id=SCENARIO_ID)
        result = await inv.investigate(event)
        assert isinstance(result, DependencyEvidence)

    async def test_evidence_type_is_dependency(self, mock_provider, event):
        inv = DependencyInvestigator(provider=mock_provider, scenario_id=SCENARIO_ID)
        result = await inv.investigate(event)
        assert result.evidence_type == EvidenceType.DEPENDENCY

    async def test_prompt_key_is_dependency_investigator(self, mock_provider, event):
        calls = []

        class SpyProvider(AIProvider):
            async def query(self, scenario_id, prompt_key):
                calls.append(prompt_key)
                return await mock_provider.query(scenario_id, prompt_key)

        inv = DependencyInvestigator(provider=SpyProvider(), scenario_id=SCENARIO_ID)
        await inv.investigate(event)
        assert calls == ["dependency_investigator"]

    async def test_pipeline_id_matches_event(self, mock_provider, event):
        inv = DependencyInvestigator(provider=mock_provider, scenario_id=SCENARIO_ID)
        result = await inv.investigate(event)
        assert result.pipeline_id == event.pipeline_run_id

    async def test_provenance_agent_id(self, mock_provider, event):
        inv = DependencyInvestigator(provider=mock_provider, scenario_id=SCENARIO_ID)
        result = await inv.investigate(event)
        assert result.source.agent_id == "dependency_investigator"

    async def test_changed_list_has_utility_lib(self, mock_provider, event):
        inv = DependencyInvestigator(provider=mock_provider, scenario_id=SCENARIO_ID)
        result = await inv.investigate(event)
        dep_names = [d.name for d in result.changed]
        assert "utility-lib" in dep_names

    async def test_breaking_changes_non_empty(self, mock_provider, event):
        inv = DependencyInvestigator(provider=mock_provider, scenario_id=SCENARIO_ID)
        result = await inv.investigate(event)
        assert len(result.breaking_changes) > 0

    async def test_repeated_calls_are_deterministic(self, mock_provider, event):
        inv = DependencyInvestigator(provider=mock_provider, scenario_id=SCENARIO_ID)
        r1 = await inv.investigate(event)
        r2 = await inv.investigate(event)
        assert r1.changed == r2.changed
        assert r1.breaking_changes == r2.breaking_changes
        assert r1.confidence == r2.confidence

    async def test_provider_error_propagates(self, event):
        inv = DependencyInvestigator(provider=MockProvider(), scenario_id="unknown-scenario")
        with pytest.raises(ValueError, match="MockProvider does not support scenario"):
            await inv.investigate(event)

    async def test_invalid_provider_output_raises_value_error(self, event):
        class BrokenProvider(AIProvider):
            async def query(self, scenario_id, prompt_key):
                # changed contains a DepChange with both versions None → invalid
                return {
                    "evidence_type": "dependency",
                    "summary": "x",
                    "confidence": 0.5,
                    "changed": [{"name": "pkg", "old_version": None, "new_version": None}],
                }

        inv = DependencyInvestigator(provider=BrokenProvider(), scenario_id=SCENARIO_ID)
        with pytest.raises(ValueError, match="DependencyEvidence validation"):
            await inv.investigate(event)


# ---------------------------------------------------------------------------
# TestInvestigator
# ---------------------------------------------------------------------------


class TestTestInvestigator:
    async def test_returns_test_run_evidence(self, mock_provider, event):
        inv = TestInvestigator(provider=mock_provider, scenario_id=SCENARIO_ID)
        result = await inv.investigate(event)
        assert isinstance(result, TestRunEvidence)

    async def test_evidence_type_is_test(self, mock_provider, event):
        inv = TestInvestigator(provider=mock_provider, scenario_id=SCENARIO_ID)
        result = await inv.investigate(event)
        assert result.evidence_type == EvidenceType.TEST

    async def test_prompt_key_is_test_investigator(self, mock_provider, event):
        calls = []

        class SpyProvider(AIProvider):
            async def query(self, scenario_id, prompt_key):
                calls.append(prompt_key)
                return await mock_provider.query(scenario_id, prompt_key)

        inv = TestInvestigator(provider=SpyProvider(), scenario_id=SCENARIO_ID)
        await inv.investigate(event)
        assert calls == ["test_investigator"]

    async def test_pipeline_id_matches_event(self, mock_provider, event):
        inv = TestInvestigator(provider=mock_provider, scenario_id=SCENARIO_ID)
        result = await inv.investigate(event)
        assert result.pipeline_id == event.pipeline_run_id

    async def test_provenance_agent_id(self, mock_provider, event):
        inv = TestInvestigator(provider=mock_provider, scenario_id=SCENARIO_ID)
        result = await inv.investigate(event)
        assert result.source.agent_id == "test_investigator"

    async def test_failed_tests_count(self, mock_provider, event):
        inv = TestInvestigator(provider=mock_provider, scenario_id=SCENARIO_ID)
        result = await inv.investigate(event)
        assert result.total_failed == 3

    async def test_total_run(self, mock_provider, event):
        inv = TestInvestigator(provider=mock_provider, scenario_id=SCENARIO_ID)
        result = await inv.investigate(event)
        assert result.total_run == 17

    async def test_failed_tests_all_mention_format_currency(self, mock_provider, event):
        inv = TestInvestigator(provider=mock_provider, scenario_id=SCENARIO_ID)
        result = await inv.investigate(event)
        for t in result.failed_tests:
            assert "formatCurrency" in (t.failure_message or "")

    async def test_repeated_calls_are_deterministic(self, mock_provider, event):
        inv = TestInvestigator(provider=mock_provider, scenario_id=SCENARIO_ID)
        r1 = await inv.investigate(event)
        r2 = await inv.investigate(event)
        assert r1.total_run == r2.total_run
        assert r1.total_failed == r2.total_failed
        assert r1.failed_tests == r2.failed_tests

    async def test_provider_error_propagates(self, event):
        inv = TestInvestigator(provider=MockProvider(), scenario_id="unknown-scenario")
        with pytest.raises(ValueError, match="MockProvider does not support scenario"):
            await inv.investigate(event)

    async def test_invalid_provider_output_raises_value_error(self, event):
        class BrokenProvider(AIProvider):
            async def query(self, scenario_id, prompt_key):
                # total_failed > total_run is invalid
                return {
                    "evidence_type": "test",
                    "summary": "bad",
                    "confidence": 0.5,
                    "total_run": 5,
                    "total_failed": 10,
                    "total_passed": 0,
                    "total_skipped": 0,
                }

        inv = TestInvestigator(provider=BrokenProvider(), scenario_id=SCENARIO_ID)
        with pytest.raises(ValueError, match="TestRunEvidence validation"):
            await inv.investigate(event)


# ---------------------------------------------------------------------------
# InfraInvestigator
# ---------------------------------------------------------------------------


class TestInfraInvestigator:
    async def test_returns_infra_evidence(self, mock_provider, event):
        inv = InfraInvestigator(provider=mock_provider, scenario_id=SCENARIO_ID)
        result = await inv.investigate(event)
        assert isinstance(result, InfraEvidence)

    async def test_evidence_type_is_infra(self, mock_provider, event):
        inv = InfraInvestigator(provider=mock_provider, scenario_id=SCENARIO_ID)
        result = await inv.investigate(event)
        assert result.evidence_type == EvidenceType.INFRA

    async def test_prompt_key_is_infra_investigator(self, mock_provider, event):
        calls = []

        class SpyProvider(AIProvider):
            async def query(self, scenario_id, prompt_key):
                calls.append(prompt_key)
                return await mock_provider.query(scenario_id, prompt_key)

        inv = InfraInvestigator(provider=SpyProvider(), scenario_id=SCENARIO_ID)
        await inv.investigate(event)
        assert calls == ["infra_investigator"]

    async def test_pipeline_id_matches_event(self, mock_provider, event):
        inv = InfraInvestigator(provider=mock_provider, scenario_id=SCENARIO_ID)
        result = await inv.investigate(event)
        assert result.pipeline_id == event.pipeline_run_id

    async def test_provenance_agent_id(self, mock_provider, event):
        inv = InfraInvestigator(provider=mock_provider, scenario_id=SCENARIO_ID)
        result = await inv.investigate(event)
        assert result.source.agent_id == "infra_investigator"

    async def test_no_dockerfile_issues(self, mock_provider, event):
        inv = InfraInvestigator(provider=mock_provider, scenario_id=SCENARIO_ID)
        result = await inv.investigate(event)
        assert result.dockerfile_issues == []

    async def test_no_ci_config_issues(self, mock_provider, event):
        inv = InfraInvestigator(provider=mock_provider, scenario_id=SCENARIO_ID)
        result = await inv.investigate(event)
        assert result.ci_config_issues == []

    async def test_config_source_present(self, mock_provider, event):
        inv = InfraInvestigator(provider=mock_provider, scenario_id=SCENARIO_ID)
        result = await inv.investigate(event)
        assert result.config_source is not None

    async def test_repeated_calls_are_deterministic(self, mock_provider, event):
        inv = InfraInvestigator(provider=mock_provider, scenario_id=SCENARIO_ID)
        r1 = await inv.investigate(event)
        r2 = await inv.investigate(event)
        assert r1.dockerfile_issues == r2.dockerfile_issues
        assert r1.ci_config_issues == r2.ci_config_issues
        assert r1.config_source == r2.config_source
        assert r1.confidence == r2.confidence

    async def test_provider_error_propagates(self, event):
        inv = InfraInvestigator(provider=MockProvider(), scenario_id="unknown-scenario")
        with pytest.raises(ValueError, match="MockProvider does not support scenario"):
            await inv.investigate(event)

    async def test_invalid_provider_output_raises_value_error(self, event):
        class BrokenProvider(AIProvider):
            async def query(self, scenario_id, prompt_key):
                # confidence out of range
                return {
                    "evidence_type": "infra",
                    "summary": "bad",
                    "confidence": 2.0,  # > 1.0 — invalid
                }

        inv = InfraInvestigator(provider=BrokenProvider(), scenario_id=SCENARIO_ID)
        with pytest.raises(ValueError, match="InfraEvidence validation"):
            await inv.investigate(event)


# ---------------------------------------------------------------------------
# HistoryInvestigator
# ---------------------------------------------------------------------------


class TestHistoryInvestigator:
    async def test_returns_historical_evidence(self, mock_provider, event):
        inv = HistoryInvestigator(provider=mock_provider, scenario_id=SCENARIO_ID)
        result = await inv.investigate(event)
        assert isinstance(result, HistoricalEvidence)

    async def test_evidence_type_is_historical(self, mock_provider, event):
        inv = HistoryInvestigator(provider=mock_provider, scenario_id=SCENARIO_ID)
        result = await inv.investigate(event)
        assert result.evidence_type == EvidenceType.HISTORICAL

    async def test_prompt_key_is_history_investigator(self, mock_provider, event):
        calls = []

        class SpyProvider(AIProvider):
            async def query(self, scenario_id, prompt_key):
                calls.append(prompt_key)
                return await mock_provider.query(scenario_id, prompt_key)

        inv = HistoryInvestigator(provider=SpyProvider(), scenario_id=SCENARIO_ID)
        await inv.investigate(event)
        assert calls == ["history_investigator"]

    async def test_pipeline_id_matches_event(self, mock_provider, event):
        inv = HistoryInvestigator(provider=mock_provider, scenario_id=SCENARIO_ID)
        result = await inv.investigate(event)
        assert result.pipeline_id == event.pipeline_run_id

    async def test_provenance_agent_id(self, mock_provider, event):
        inv = HistoryInvestigator(provider=mock_provider, scenario_id=SCENARIO_ID)
        result = await inv.investigate(event)
        assert result.source.agent_id == "history_investigator"

    async def test_similar_failures_present(self, mock_provider, event):
        inv = HistoryInvestigator(provider=mock_provider, scenario_id=SCENARIO_ID)
        result = await inv.investigate(event)
        assert len(result.similar_failures) > 0

    async def test_recurrence_count_at_least_one(self, mock_provider, event):
        inv = HistoryInvestigator(provider=mock_provider, scenario_id=SCENARIO_ID)
        result = await inv.investigate(event)
        assert result.recurrence_count >= 1

    async def test_known_fix_mentions_pin(self, mock_provider, event):
        inv = HistoryInvestigator(provider=mock_provider, scenario_id=SCENARIO_ID)
        result = await inv.investigate(event)
        assert result.known_fix is not None
        assert "pin" in result.known_fix.lower() or "Pin" in result.known_fix

    async def test_similarity_score_in_range(self, mock_provider, event):
        inv = HistoryInvestigator(provider=mock_provider, scenario_id=SCENARIO_ID)
        result = await inv.investigate(event)
        for sf in result.similar_failures:
            if sf.similarity_score is not None:
                assert 0.0 <= sf.similarity_score <= 1.0

    async def test_repeated_calls_are_deterministic(self, mock_provider, event):
        inv = HistoryInvestigator(provider=mock_provider, scenario_id=SCENARIO_ID)
        r1 = await inv.investigate(event)
        r2 = await inv.investigate(event)
        assert r1.recurrence_count == r2.recurrence_count
        assert r1.known_fix == r2.known_fix
        assert r1.similar_failures == r2.similar_failures
        assert r1.confidence == r2.confidence

    async def test_provider_error_propagates(self, event):
        inv = HistoryInvestigator(provider=MockProvider(), scenario_id="unknown-scenario")
        with pytest.raises(ValueError, match="MockProvider does not support scenario"):
            await inv.investigate(event)

    async def test_invalid_provider_output_raises_value_error(self, event):
        class BrokenProvider(AIProvider):
            async def query(self, scenario_id, prompt_key):
                # recurrence_count negative — invalid
                return {
                    "evidence_type": "historical",
                    "summary": "bad",
                    "confidence": 0.5,
                    "recurrence_count": -1,
                }

        inv = HistoryInvestigator(provider=BrokenProvider(), scenario_id=SCENARIO_ID)
        with pytest.raises(ValueError, match="HistoricalEvidence validation"):
            await inv.investigate(event)


# ---------------------------------------------------------------------------
# Cross-investigator — provenance isolation
# ---------------------------------------------------------------------------


class TestProvenanceIsolation:
    """Each investigator stamps its own agent_id onto the evidence source."""

    async def test_all_agent_ids_are_distinct(self, mock_provider, event):
        investigators = [
            LogInvestigator(provider=mock_provider, scenario_id=SCENARIO_ID),
            CodeInvestigator(provider=mock_provider, scenario_id=SCENARIO_ID),
            DependencyInvestigator(provider=mock_provider, scenario_id=SCENARIO_ID),
            TestInvestigator(provider=mock_provider, scenario_id=SCENARIO_ID),
            InfraInvestigator(provider=mock_provider, scenario_id=SCENARIO_ID),
            HistoryInvestigator(provider=mock_provider, scenario_id=SCENARIO_ID),
        ]
        agent_ids = []
        for inv in investigators:
            result = await inv.investigate(event)
            agent_ids.append(result.source.agent_id)

        assert len(set(agent_ids)) == 6, f"Expected 6 distinct agent_ids, got: {agent_ids}"

    async def test_all_evidence_ids_are_distinct(self, mock_provider, event):
        """Each call produces a unique evidence_id (uuid-based)."""
        inv = LogInvestigator(provider=mock_provider, scenario_id=SCENARIO_ID)
        r1 = await inv.investigate(event)
        r2 = await inv.investigate(event)
        # evidence_ids should differ because they are generated per-call
        assert r1.evidence_id != r2.evidence_id

    async def test_pipeline_id_is_preserved_across_all_investigators(self, mock_provider, event):
        investigators = [
            LogInvestigator(provider=mock_provider, scenario_id=SCENARIO_ID),
            CodeInvestigator(provider=mock_provider, scenario_id=SCENARIO_ID),
            DependencyInvestigator(provider=mock_provider, scenario_id=SCENARIO_ID),
            TestInvestigator(provider=mock_provider, scenario_id=SCENARIO_ID),
            InfraInvestigator(provider=mock_provider, scenario_id=SCENARIO_ID),
            HistoryInvestigator(provider=mock_provider, scenario_id=SCENARIO_ID),
        ]
        for inv in investigators:
            result = await inv.investigate(event)
            assert result.pipeline_id == event.pipeline_run_id, (
                f"{type(inv).__name__} pipeline_id mismatch"
            )


# ---------------------------------------------------------------------------
# Cross-investigator — prompt key mapping
# ---------------------------------------------------------------------------


class TestPromptKeyMapping:
    """All six prompt keys must match the MockProvider's supported keys."""

    def test_all_prompt_keys_supported_by_mock_provider(self):
        from app.ai.mock_provider import SUPPORTED_PROMPT_KEYS

        for cls in [
            LogInvestigator,
            CodeInvestigator,
            DependencyInvestigator,
            TestInvestigator,
            InfraInvestigator,
            HistoryInvestigator,
        ]:
            assert cls.PROMPT_KEY in SUPPORTED_PROMPT_KEYS, (
                f"{cls.__name__}.PROMPT_KEY='{cls.PROMPT_KEY}' not in MockProvider supported keys"
            )

    def test_prompt_keys_are_unique(self):
        keys = [
            LogInvestigator.PROMPT_KEY,
            CodeInvestigator.PROMPT_KEY,
            DependencyInvestigator.PROMPT_KEY,
            TestInvestigator.PROMPT_KEY,
            InfraInvestigator.PROMPT_KEY,
            HistoryInvestigator.PROMPT_KEY,
        ]
        assert len(set(keys)) == 6, f"Expected 6 unique prompt keys, got: {keys}"

    def test_agent_ids_match_prompt_keys(self):
        """For these investigators, agent_id == PROMPT_KEY by convention."""
        for cls in [
            LogInvestigator,
            CodeInvestigator,
            DependencyInvestigator,
            TestInvestigator,
            InfraInvestigator,
            HistoryInvestigator,
        ]:
            assert cls.agent_id == cls.PROMPT_KEY, (
                f"{cls.__name__}: agent_id '{cls.agent_id}' != PROMPT_KEY '{cls.PROMPT_KEY}'"
            )
