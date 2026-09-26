"""
Unit tests for MockProvider (Task 4).

Coverage
--------
- Provider initializes correctly (no arguments needed)
- AIProvider abstract interface is enforced
- scenario-001 is recognized
- Each of the six investigator prompt keys returns deterministic data
- Repeated calls return equivalent (but independent) dicts
- Returned dicts can be validated against the expected Pydantic evidence schemas
- Unsupported prompt key raises ValueError with a clear message
- Unsupported scenario raises ValueError with a clear message
- No external network / API call is made (purely in-process)
- SUPPORTED_PROMPT_KEYS constant is correct
"""

from __future__ import annotations

import inspect
import pytest

from app.ai.provider import AIProvider
from app.ai.mock_provider import MockProvider, SUPPORTED_PROMPT_KEYS
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
# Shared helpers
# ---------------------------------------------------------------------------

SCENARIO_ID = "scenario-001"

# Minimum identity fields every evidence model requires that MockProvider
# intentionally omits (they are caller-supplied at run-time).
_IDENTITY = {
    "evidence_id": "ev-mock-test",
    "pipeline_id": "pipe-mock-test",
    "source": EvidenceSource(
        agent_id="test_agent",
        input_file="mock",
        extraction_method="mock",
    ),
}


def _build(raw: dict, cls):
    """Merge identity fields and construct an evidence model."""
    return cls(**{**_IDENTITY, **raw})


# ---------------------------------------------------------------------------
# Initialization and interface
# ---------------------------------------------------------------------------


class TestMockProviderInit:
    def test_instantiates_without_arguments(self):
        provider = MockProvider()
        assert provider is not None

    def test_is_subclass_of_aiprovider(self):
        assert issubclass(MockProvider, AIProvider)

    def test_instance_is_aiprovider(self):
        provider = MockProvider()
        assert isinstance(provider, AIProvider)

    def test_aiprovider_is_abstract(self):
        """AIProvider cannot be instantiated directly — it is abstract."""
        with pytest.raises(TypeError):
            AIProvider()  # type: ignore[abstract]

    def test_query_method_is_coroutine(self):
        """query() must be awaitable (async)."""
        provider = MockProvider()
        assert inspect.iscoroutinefunction(provider.query)

    def test_supported_prompt_keys_constant(self):
        expected = {
            "log_investigator",
            "code_investigator",
            "dependency_investigator",
            "test_investigator",
            "infra_investigator",
            "history_investigator",
        }
        assert SUPPORTED_PROMPT_KEYS == expected


# ---------------------------------------------------------------------------
# Scenario recognition
# ---------------------------------------------------------------------------


class TestScenarioRecognition:
    async def test_scenario_001_recognized(self):
        provider = MockProvider()
        # Should not raise
        raw = await provider.query(SCENARIO_ID, "log_investigator")
        assert isinstance(raw, dict)

    async def test_unknown_scenario_raises_value_error(self):
        provider = MockProvider()
        with pytest.raises(ValueError, match="scenario-999"):
            await provider.query("scenario-999", "log_investigator")

    async def test_unknown_scenario_message_lists_supported(self):
        provider = MockProvider()
        with pytest.raises(ValueError, match="scenario-001"):
            await provider.query("totally-unknown", "log_investigator")

    async def test_empty_scenario_id_raises(self):
        provider = MockProvider()
        with pytest.raises(ValueError):
            await provider.query("", "log_investigator")


# ---------------------------------------------------------------------------
# Unsupported prompt key
# ---------------------------------------------------------------------------


class TestUnsupportedPromptKey:
    async def test_unknown_key_raises_value_error(self):
        provider = MockProvider()
        with pytest.raises(ValueError, match="not_a_real_key"):
            await provider.query(SCENARIO_ID, "not_a_real_key")

    async def test_error_message_lists_supported_keys(self):
        provider = MockProvider()
        with pytest.raises(ValueError, match="log_investigator"):
            await provider.query(SCENARIO_ID, "does_not_exist")

    async def test_empty_prompt_key_raises(self):
        provider = MockProvider()
        with pytest.raises(ValueError):
            await provider.query(SCENARIO_ID, "")


# ---------------------------------------------------------------------------
# log_investigator → FailureEvidence
# ---------------------------------------------------------------------------


class TestLogInvestigatorKey:
    async def test_returns_dict(self):
        raw = await MockProvider().query(SCENARIO_ID, "log_investigator")
        assert isinstance(raw, dict)

    async def test_evidence_type_is_failure(self):
        raw = await MockProvider().query(SCENARIO_ID, "log_investigator")
        assert raw["evidence_type"] == "failure"

    async def test_required_failure_fields_present(self):
        raw = await MockProvider().query(SCENARIO_ID, "log_investigator")
        assert "error_class" in raw
        assert "error_message" in raw
        assert "affected_stage" in raw

    async def test_error_class_is_type_error(self):
        raw = await MockProvider().query(SCENARIO_ID, "log_investigator")
        assert raw["error_class"] == "TypeError"

    async def test_error_message_matches_scenario(self):
        raw = await MockProvider().query(SCENARIO_ID, "log_investigator")
        assert "formatCurrency" in raw["error_message"]

    async def test_affected_stage_is_test(self):
        raw = await MockProvider().query(SCENARIO_ID, "log_investigator")
        assert raw["affected_stage"] == "test"

    async def test_severity_is_critical(self):
        raw = await MockProvider().query(SCENARIO_ID, "log_investigator")
        assert raw["severity"] == "critical"

    async def test_stack_trace_is_list(self):
        raw = await MockProvider().query(SCENARIO_ID, "log_investigator")
        assert isinstance(raw["stack_trace"], list)
        assert len(raw["stack_trace"]) > 0

    async def test_file_path_present(self):
        raw = await MockProvider().query(SCENARIO_ID, "log_investigator")
        assert raw["file_path"] == "src/payments/invoice.js"

    async def test_line_number_present(self):
        raw = await MockProvider().query(SCENARIO_ID, "log_investigator")
        assert raw["line_number"] == 12

    async def test_confidence_in_range(self):
        raw = await MockProvider().query(SCENARIO_ID, "log_investigator")
        assert 0.0 <= raw["confidence"] <= 1.0

    async def test_validates_against_failure_evidence_schema(self):
        raw = await MockProvider().query(SCENARIO_ID, "log_investigator")
        ev = _build(raw, FailureEvidence)
        assert ev.evidence_type == EvidenceType.FAILURE
        assert ev.error_class == "TypeError"
        assert ev.severity == Severity.CRITICAL
        assert ev.affected_stage == "test"
        assert ev.line_number == 12


# ---------------------------------------------------------------------------
# code_investigator → ChangeEvidence
# ---------------------------------------------------------------------------


class TestCodeInvestigatorKey:
    async def test_returns_dict(self):
        raw = await MockProvider().query(SCENARIO_ID, "code_investigator")
        assert isinstance(raw, dict)

    async def test_evidence_type_is_change(self):
        raw = await MockProvider().query(SCENARIO_ID, "code_investigator")
        assert raw["evidence_type"] == "change"

    async def test_commit_sha_present(self):
        raw = await MockProvider().query(SCENARIO_ID, "code_investigator")
        assert raw["commit_sha"].startswith("a1b2c3d4")

    async def test_changed_files_contains_package_json(self):
        raw = await MockProvider().query(SCENARIO_ID, "code_investigator")
        paths = [f["path"] for f in raw["changed_files"]]
        assert "package.json" in paths

    async def test_diff_hunk_shows_version_bump(self):
        raw = await MockProvider().query(SCENARIO_ID, "code_investigator")
        hunk = raw["changed_files"][0]["diff_hunk"]
        assert "2.3.1" in hunk
        assert "3.0.0" in hunk

    async def test_total_additions_and_deletions(self):
        raw = await MockProvider().query(SCENARIO_ID, "code_investigator")
        assert raw["total_additions"] == 1
        assert raw["total_deletions"] == 1

    async def test_validates_against_change_evidence_schema(self):
        raw = await MockProvider().query(SCENARIO_ID, "code_investigator")
        ev = _build(raw, ChangeEvidence)
        assert ev.evidence_type == EvidenceType.CHANGE
        assert ev.commit_sha.startswith("a1b2c3d4")
        assert len(ev.changed_files) == 1
        assert ev.changed_files[0].path == "package.json"


# ---------------------------------------------------------------------------
# dependency_investigator → DependencyEvidence
# ---------------------------------------------------------------------------


class TestDependencyInvestigatorKey:
    async def test_returns_dict(self):
        raw = await MockProvider().query(SCENARIO_ID, "dependency_investigator")
        assert isinstance(raw, dict)

    async def test_evidence_type_is_dependency(self):
        raw = await MockProvider().query(SCENARIO_ID, "dependency_investigator")
        assert raw["evidence_type"] == "dependency"

    async def test_changed_list_has_utility_lib(self):
        raw = await MockProvider().query(SCENARIO_ID, "dependency_investigator")
        names = [c["name"] for c in raw["changed"]]
        assert "utility-lib" in names

    async def test_version_bump_values(self):
        raw = await MockProvider().query(SCENARIO_ID, "dependency_investigator")
        dep = raw["changed"][0]
        assert dep["old_version"] == "2.3.1"
        assert dep["new_version"] == "3.0.0"

    async def test_breaking_changes_non_empty(self):
        raw = await MockProvider().query(SCENARIO_ID, "dependency_investigator")
        assert len(raw["breaking_changes"]) >= 1
        assert "formatCurrency" in raw["breaking_changes"][0]

    async def test_validates_against_dependency_evidence_schema(self):
        raw = await MockProvider().query(SCENARIO_ID, "dependency_investigator")
        ev = _build(raw, DependencyEvidence)
        assert ev.evidence_type == EvidenceType.DEPENDENCY
        assert ev.changed[0].name == "utility-lib"
        assert ev.changed[0].old_version == "2.3.1"
        assert ev.changed[0].new_version == "3.0.0"
        assert len(ev.breaking_changes) >= 1


# ---------------------------------------------------------------------------
# test_investigator → TestRunEvidence
# ---------------------------------------------------------------------------


class TestTestInvestigatorKey:
    async def test_returns_dict(self):
        raw = await MockProvider().query(SCENARIO_ID, "test_investigator")
        assert isinstance(raw, dict)

    async def test_evidence_type_is_test(self):
        raw = await MockProvider().query(SCENARIO_ID, "test_investigator")
        assert raw["evidence_type"] == "test"

    async def test_total_run_17(self):
        raw = await MockProvider().query(SCENARIO_ID, "test_investigator")
        assert raw["total_run"] == 17

    async def test_total_failed_3(self):
        raw = await MockProvider().query(SCENARIO_ID, "test_investigator")
        assert raw["total_failed"] == 3

    async def test_total_passed_14(self):
        raw = await MockProvider().query(SCENARIO_ID, "test_investigator")
        assert raw["total_passed"] == 14

    async def test_three_failed_test_entries(self):
        raw = await MockProvider().query(SCENARIO_ID, "test_investigator")
        assert len(raw["failed_tests"]) == 3

    async def test_all_failures_mention_format_currency(self):
        raw = await MockProvider().query(SCENARIO_ID, "test_investigator")
        for ft in raw["failed_tests"]:
            assert "formatCurrency" in ft["failure_message"]

    async def test_regression_tests_match_failed_tests(self):
        raw = await MockProvider().query(SCENARIO_ID, "test_investigator")
        failed_names = {ft["name"] for ft in raw["failed_tests"]}
        regression_names = set(raw["regression_tests"])
        assert regression_names == failed_names

    async def test_validates_against_test_run_evidence_schema(self):
        raw = await MockProvider().query(SCENARIO_ID, "test_investigator")
        ev = _build(raw, TestRunEvidence)
        assert ev.evidence_type == EvidenceType.TEST
        assert ev.total_run == 17
        assert ev.total_failed == 3
        assert ev.total_passed == 14
        assert len(ev.failed_tests) == 3


# ---------------------------------------------------------------------------
# infra_investigator → InfraEvidence
# ---------------------------------------------------------------------------


class TestInfraInvestigatorKey:
    async def test_returns_dict(self):
        raw = await MockProvider().query(SCENARIO_ID, "infra_investigator")
        assert isinstance(raw, dict)

    async def test_evidence_type_is_infra(self):
        raw = await MockProvider().query(SCENARIO_ID, "infra_investigator")
        assert raw["evidence_type"] == "infra"

    async def test_no_dockerfile_issues(self):
        raw = await MockProvider().query(SCENARIO_ID, "infra_investigator")
        assert raw["dockerfile_issues"] == []

    async def test_no_ci_config_issues(self):
        raw = await MockProvider().query(SCENARIO_ID, "infra_investigator")
        assert raw["ci_config_issues"] == []

    async def test_config_source_present(self):
        raw = await MockProvider().query(SCENARIO_ID, "infra_investigator")
        assert raw["config_source"] is not None

    async def test_validates_against_infra_evidence_schema(self):
        raw = await MockProvider().query(SCENARIO_ID, "infra_investigator")
        ev = _build(raw, InfraEvidence)
        assert ev.evidence_type == EvidenceType.INFRA
        assert ev.dockerfile_issues == []
        assert ev.ci_config_issues == []
        assert ev.config_source == ".github/workflows/ci.yml"


# ---------------------------------------------------------------------------
# history_investigator → HistoricalEvidence
# ---------------------------------------------------------------------------


class TestHistoryInvestigatorKey:
    async def test_returns_dict(self):
        raw = await MockProvider().query(SCENARIO_ID, "history_investigator")
        assert isinstance(raw, dict)

    async def test_evidence_type_is_historical(self):
        raw = await MockProvider().query(SCENARIO_ID, "history_investigator")
        assert raw["evidence_type"] == "historical"

    async def test_similar_failure_present(self):
        raw = await MockProvider().query(SCENARIO_ID, "history_investigator")
        assert len(raw["similar_failures"]) >= 1

    async def test_prior_failure_run_id(self):
        raw = await MockProvider().query(SCENARIO_ID, "history_investigator")
        assert raw["similar_failures"][0]["run_id"] == "run-20240108-007"

    async def test_recurrence_count_at_least_one(self):
        raw = await MockProvider().query(SCENARIO_ID, "history_investigator")
        assert raw["recurrence_count"] >= 1

    async def test_known_fix_mentions_pin(self):
        raw = await MockProvider().query(SCENARIO_ID, "history_investigator")
        assert raw["known_fix"] is not None
        assert "2.3.1" in raw["known_fix"]

    async def test_similarity_score_in_range(self):
        raw = await MockProvider().query(SCENARIO_ID, "history_investigator")
        score = raw["similar_failures"][0]["similarity_score"]
        assert 0.0 <= score <= 1.0

    async def test_validates_against_historical_evidence_schema(self):
        raw = await MockProvider().query(SCENARIO_ID, "history_investigator")
        ev = _build(raw, HistoricalEvidence)
        assert ev.evidence_type == EvidenceType.HISTORICAL
        assert ev.recurrence_count >= 1
        assert ev.known_fix is not None
        assert len(ev.similar_failures) >= 1
        assert ev.similar_failures[0].run_id == "run-20240108-007"


# ---------------------------------------------------------------------------
# Determinism — repeated calls must return equivalent results
# ---------------------------------------------------------------------------


class TestDeterminism:
    async def test_log_investigator_same_result_twice(self):
        provider = MockProvider()
        r1 = await provider.query(SCENARIO_ID, "log_investigator")
        r2 = await provider.query(SCENARIO_ID, "log_investigator")
        assert r1 == r2

    async def test_dependency_investigator_same_result_twice(self):
        provider = MockProvider()
        r1 = await provider.query(SCENARIO_ID, "dependency_investigator")
        r2 = await provider.query(SCENARIO_ID, "dependency_investigator")
        assert r1 == r2

    async def test_results_are_independent_copies(self):
        """Mutating one result must not affect the next call's result."""
        provider = MockProvider()
        r1 = await provider.query(SCENARIO_ID, "log_investigator")
        r1["confidence"] = 0.0  # mutate the copy
        r2 = await provider.query(SCENARIO_ID, "log_investigator")
        assert r2["confidence"] != 0.0

    async def test_all_six_keys_deterministic(self):
        provider = MockProvider()
        for key in SUPPORTED_PROMPT_KEYS:
            a = await provider.query(SCENARIO_ID, key)
            b = await provider.query(SCENARIO_ID, key)
            assert a == b, f"Non-determinism detected for prompt_key='{key}'"

    async def test_two_provider_instances_same_result(self):
        """Different instances must return the same data."""
        p1 = MockProvider()
        p2 = MockProvider()
        r1 = await p1.query(SCENARIO_ID, "test_investigator")
        r2 = await p2.query(SCENARIO_ID, "test_investigator")
        assert r1 == r2


# ---------------------------------------------------------------------------
# No external calls
# ---------------------------------------------------------------------------


class TestNoExternalCalls:
    async def test_all_keys_resolve_without_network(self, monkeypatch):
        """
        Block all socket connections; MockProvider must still work perfectly.
        The monkeypatch blocks socket.socket at import time — if any code
        accidentally tries to open a connection this test will error.
        """
        import socket

        original_connect = socket.socket.connect

        def _no_connect(self, address):
            raise AssertionError(
                f"MockProvider made an unexpected network call to {address!r}"
            )

        monkeypatch.setattr(socket.socket, "connect", _no_connect)

        provider = MockProvider()
        for key in SUPPORTED_PROMPT_KEYS:
            raw = await provider.query(SCENARIO_ID, key)
            assert isinstance(raw, dict)


# ---------------------------------------------------------------------------
# Schema round-trips — all six models survive JSON round-trip
# ---------------------------------------------------------------------------


class TestSchemaRoundTrips:
    """
    Each evidence model produced from MockProvider data must survive
    model → JSON → model without data loss.
    """

    def _roundtrip(self, model):
        import json

        json_str = model.model_dump_json()
        data = json.loads(json_str)
        reconstructed = model.__class__.model_validate(data)
        assert reconstructed == model

    async def test_failure_evidence_roundtrip(self):
        raw = await MockProvider().query(SCENARIO_ID, "log_investigator")
        ev = _build(raw, FailureEvidence)
        self._roundtrip(ev)

    async def test_change_evidence_roundtrip(self):
        raw = await MockProvider().query(SCENARIO_ID, "code_investigator")
        ev = _build(raw, ChangeEvidence)
        self._roundtrip(ev)

    async def test_dependency_evidence_roundtrip(self):
        raw = await MockProvider().query(SCENARIO_ID, "dependency_investigator")
        ev = _build(raw, DependencyEvidence)
        self._roundtrip(ev)

    async def test_test_run_evidence_roundtrip(self):
        raw = await MockProvider().query(SCENARIO_ID, "test_investigator")
        ev = _build(raw, TestRunEvidence)
        self._roundtrip(ev)

    async def test_infra_evidence_roundtrip(self):
        raw = await MockProvider().query(SCENARIO_ID, "infra_investigator")
        ev = _build(raw, InfraEvidence)
        self._roundtrip(ev)

    async def test_historical_evidence_roundtrip(self):
        raw = await MockProvider().query(SCENARIO_ID, "history_investigator")
        ev = _build(raw, HistoricalEvidence)
        self._roundtrip(ev)
