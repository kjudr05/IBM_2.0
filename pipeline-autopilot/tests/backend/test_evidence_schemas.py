"""
Unit tests for all evidence artifact schemas (Task 2).

Covers:
- Valid construction of each evidence subclass
- Validation failure for invalid required fields
- Confidence range enforcement (0.0–1.0)
- JSON serialization round-trips
- Optional field behaviour (None defaults, acceptance when provided)
- EvidenceSource provenance fields
- Supporting value object validation (DepChange, FailedTest, etc.)
- Discriminator field (evidence_type) correctness
- Cross-field validators (TestEvidence count consistency, DepChange version rule)
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.models.evidence import (
    ChangedFile,
    ChangeEvidence,
    DepChange,
    DependencyEvidence,
    EvidenceSource,
    EvidenceType,
    FailedTest,
    FailureEvidence,
    HistoricalEvidence,
    InfraEvidence,
    Severity,
    SimilarFailure,
    TestCaseStatus,
    TestEvidence,
)
from app.models.events import HistoricalRun, PipelineFailureEvent


# ---------------------------------------------------------------------------
# Fixtures — minimal valid data builders
# ---------------------------------------------------------------------------


def make_source(agent_id: str = "test_agent") -> EvidenceSource:
    return EvidenceSource(
        agent_id=agent_id,
        input_file="ci_log.txt",
        extraction_method="mock",
    )


def base_kwargs(evidence_type: EvidenceType) -> dict:
    """Minimum kwargs valid for any BaseEvidence subclass."""
    return {
        "evidence_id": "ev-001",
        "pipeline_id": "pipe-001",
        "evidence_type": evidence_type,
        "source": make_source(),
        "summary": "Something went wrong",
        "confidence": 0.9,
    }


# ---------------------------------------------------------------------------
# EvidenceSource
# ---------------------------------------------------------------------------


class TestEvidenceSource:
    def test_valid_full(self):
        src = EvidenceSource(
            agent_id="log_investigator",
            input_file="ci_log.txt",
            extraction_method="regex_parse",
        )
        assert src.agent_id == "log_investigator"
        assert src.input_file == "ci_log.txt"

    def test_valid_minimal(self):
        src = EvidenceSource(agent_id="log_investigator")
        assert src.input_file is None
        assert src.extraction_method is None

    def test_agent_id_required(self):
        with pytest.raises(ValidationError):
            EvidenceSource()  # type: ignore[call-arg]

    def test_frozen(self):
        src = EvidenceSource(agent_id="a")
        with pytest.raises(Exception):
            src.agent_id = "b"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Supporting value objects
# ---------------------------------------------------------------------------


class TestChangedFile:
    def test_valid(self):
        cf = ChangedFile(path="src/payments/invoice.js", additions=5, deletions=2)
        assert cf.path == "src/payments/invoice.js"
        assert cf.additions == 5

    def test_defaults(self):
        cf = ChangedFile(path="README.md")
        assert cf.additions == 0
        assert cf.deletions == 0
        assert cf.diff_hunk is None

    def test_negative_additions_rejected(self):
        with pytest.raises(ValidationError):
            ChangedFile(path="x.py", additions=-1)


class TestDepChange:
    def test_version_bump(self):
        dc = DepChange(name="utility-lib", old_version="2.3.1", new_version="3.0.0")
        assert dc.name == "utility-lib"

    def test_added_dep(self):
        dc = DepChange(name="lodash", new_version="4.17.21")
        assert dc.old_version is None

    def test_removed_dep(self):
        dc = DepChange(name="old-pkg", old_version="1.0.0")
        assert dc.new_version is None

    def test_both_none_rejected(self):
        with pytest.raises(ValidationError):
            DepChange(name="bad")

    def test_name_required(self):
        with pytest.raises(ValidationError):
            DepChange(old_version="1.0", new_version="2.0")  # type: ignore[call-arg]


class TestFailedTest:
    def test_valid(self):
        ft = FailedTest(
            name="test_format_invoice",
            class_name="PaymentsService",
            failure_message="TypeError: formatCurrency is not a function",
            duration_ms=12.3,
        )
        assert ft.name == "test_format_invoice"

    def test_minimal(self):
        ft = FailedTest(name="test_something")
        assert ft.class_name is None
        assert ft.failure_message is None

    def test_negative_duration_rejected(self):
        with pytest.raises(ValidationError):
            FailedTest(name="x", duration_ms=-1)


class TestSimilarFailure:
    def test_valid(self):
        sf = SimilarFailure(
            run_id="run-20240108-007",
            date=datetime(2024, 1, 8, tzinfo=timezone.utc),
            root_cause="utility-lib breaking change",
            fix_applied="Pinned to 2.1.5",
            similarity_score=0.95,
        )
        assert sf.similarity_score == 0.95

    def test_similarity_out_of_range(self):
        with pytest.raises(ValidationError):
            SimilarFailure(
                run_id="x",
                date=datetime.utcnow(),
                root_cause="y",
                similarity_score=1.5,
            )


# ---------------------------------------------------------------------------
# Confidence validation (shared across all subclasses)
# ---------------------------------------------------------------------------


class TestConfidenceValidation:
    @pytest.mark.parametrize("value", [0.0, 0.5, 1.0])
    def test_valid_range(self, value):
        kwargs = {**base_kwargs(EvidenceType.FAILURE), "confidence": value}
        ev = FailureEvidence(
            **kwargs,
            error_class="TypeError",
            error_message="formatCurrency is not a function",
            affected_stage="test",
        )
        assert ev.confidence == value

    @pytest.mark.parametrize("value", [-0.01, 1.01, 2.0, -1.0])
    def test_out_of_range_rejected(self, value):
        kwargs = {**base_kwargs(EvidenceType.FAILURE), "confidence": value}
        with pytest.raises(ValidationError):
            FailureEvidence(
                **kwargs,
                error_class="TypeError",
                error_message="msg",
                affected_stage="test",
            )


# ---------------------------------------------------------------------------
# FailureEvidence
# ---------------------------------------------------------------------------


class TestFailureEvidence:
    def _make(self, **overrides) -> FailureEvidence:
        kwargs = {
            **base_kwargs(EvidenceType.FAILURE),
            "error_class": "TypeError",
            "error_message": "formatCurrency is not a function",
            "affected_stage": "test",
        }
        kwargs.update(overrides)
        return FailureEvidence(**kwargs)

    def test_valid_minimal(self):
        ev = self._make()
        assert ev.evidence_type == EvidenceType.FAILURE
        assert ev.error_class == "TypeError"
        assert ev.severity == Severity.HIGH  # default

    def test_valid_full(self):
        ev = self._make(
            stack_trace=["  at invoice.js:12", "  at test.js:23"],
            failure_timestamp=datetime(2024, 3, 15, 14, 32, 16, tzinfo=timezone.utc),
            severity=Severity.CRITICAL,
            log_excerpt="[14:32:16] TypeError: formatCurrency...",
            file_path="src/payments/invoice.js",
            line_number=12,
        )
        assert len(ev.stack_trace) == 2
        assert ev.severity == Severity.CRITICAL
        assert ev.line_number == 12

    def test_discriminator_locked(self):
        ev = self._make()
        assert ev.evidence_type == EvidenceType.FAILURE

    def test_error_class_required(self):
        kwargs = {**base_kwargs(EvidenceType.FAILURE), "error_message": "x", "affected_stage": "y"}
        with pytest.raises(ValidationError):
            FailureEvidence(**kwargs)  # missing error_class

    def test_line_number_must_be_positive(self):
        with pytest.raises(ValidationError):
            self._make(line_number=0)

    def test_optional_fields_default_none(self):
        ev = self._make()
        assert ev.failure_timestamp is None
        assert ev.log_excerpt is None
        assert ev.file_path is None
        assert ev.line_number is None

    def test_source_provenance(self):
        src = EvidenceSource(
            agent_id="log_investigator",
            input_file="ci_log.txt",
            extraction_method="regex_parse",
        )
        ev = self._make(source=src)
        assert ev.source.agent_id == "log_investigator"
        assert ev.source.input_file == "ci_log.txt"


# ---------------------------------------------------------------------------
# ChangeEvidence
# ---------------------------------------------------------------------------


class TestChangeEvidence:
    def _make(self, **overrides) -> ChangeEvidence:
        kwargs = {
            **base_kwargs(EvidenceType.CHANGE),
            "commit_sha": "a1b2c3d4",
        }
        kwargs.update(overrides)
        return ChangeEvidence(**kwargs)

    def test_valid_minimal(self):
        ev = self._make()
        assert ev.evidence_type == EvidenceType.CHANGE
        assert ev.commit_sha == "a1b2c3d4"

    def test_valid_full(self):
        ev = self._make(
            author="dev@acme.com",
            commit_message="chore: bump utility-lib to 3.0.0",
            commit_timestamp=datetime(2024, 3, 15, 14, 0, tzinfo=timezone.utc),
            changed_files=[
                ChangedFile(path="package.json", additions=1, deletions=1),
            ],
            changed_functions=["formatCurrency"],
            total_additions=1,
            total_deletions=1,
        )
        assert len(ev.changed_files) == 1
        assert ev.changed_files[0].path == "package.json"

    def test_commit_sha_required(self):
        kwargs = base_kwargs(EvidenceType.CHANGE)
        with pytest.raises(ValidationError):
            ChangeEvidence(**kwargs)  # missing commit_sha

    def test_optional_author(self):
        ev = self._make()
        assert ev.author is None


# ---------------------------------------------------------------------------
# DependencyEvidence
# ---------------------------------------------------------------------------


class TestDependencyEvidence:
    def _make(self, **overrides) -> DependencyEvidence:
        kwargs = {**base_kwargs(EvidenceType.DEPENDENCY)}
        kwargs.update(overrides)
        return DependencyEvidence(**kwargs)

    def test_valid_empty_lists(self):
        ev = self._make()
        assert ev.evidence_type == EvidenceType.DEPENDENCY
        assert ev.added == []
        assert ev.breaking_changes == []

    def test_valid_with_changes(self):
        ev = self._make(
            changed=[DepChange(name="utility-lib", old_version="2.3.1", new_version="3.0.0")],
            breaking_changes=["utility-lib 3.0.0 removes formatCurrency()"],
        )
        assert len(ev.changed) == 1
        assert ev.changed[0].name == "utility-lib"
        assert len(ev.breaking_changes) == 1

    def test_dep_change_as_dict(self):
        """Agents may pass plain dicts; coerce_dep_changes should handle them."""
        ev = self._make(
            added=[{"name": "new-pkg", "new_version": "1.0.0"}],
        )
        assert ev.added[0].name == "new-pkg"


# ---------------------------------------------------------------------------
# TestEvidence
# ---------------------------------------------------------------------------


class TestTestEvidence:
    def _make(self, **overrides) -> TestEvidence:
        kwargs = {**base_kwargs(EvidenceType.TEST)}
        kwargs.update(overrides)
        return TestEvidence(**kwargs)

    def test_valid_minimal(self):
        ev = self._make()
        assert ev.evidence_type == EvidenceType.TEST
        assert ev.total_run == 0

    def test_valid_with_failures(self):
        ev = self._make(
            failed_tests=[
                FailedTest(
                    name="test_format_invoice",
                    class_name="PaymentsService",
                    failure_message="TypeError: formatCurrency is not a function",
                )
            ],
            regression_tests=["test_format_invoice"],
            total_run=17,
            total_failed=3,
            total_passed=14,
        )
        assert len(ev.failed_tests) == 1
        assert ev.total_failed == 3

    def test_flaky_tests_list(self):
        ev = self._make(flaky_tests=["test_network_call"])
        assert "test_network_call" in ev.flaky_tests

    def test_failed_exceeds_total_rejected(self):
        with pytest.raises(ValidationError):
            self._make(total_run=5, total_failed=10)

    def test_zero_totals_ok(self):
        # Both zero is valid (e.g. test stage not reached)
        ev = self._make(total_run=0, total_failed=0)
        assert ev.total_run == 0


# ---------------------------------------------------------------------------
# InfraEvidence
# ---------------------------------------------------------------------------


class TestInfraEvidence:
    def _make(self, **overrides) -> InfraEvidence:
        kwargs = {**base_kwargs(EvidenceType.INFRA)}
        kwargs.update(overrides)
        return InfraEvidence(**kwargs)

    def test_valid_no_issues(self):
        ev = self._make()
        assert ev.evidence_type == EvidenceType.INFRA
        assert ev.dockerfile_issues == []
        assert ev.ci_config_issues == []

    def test_valid_with_issues(self):
        ev = self._make(
            dockerfile_issues=["Base image outdated"],
            ci_config_issues=["Node version not pinned"],
            env_var_issues=["API_KEY missing"],
            image_changes=["node:18-alpine → node:20-alpine"],
            config_source=".github/workflows/ci.yml",
        )
        assert ev.dockerfile_issues[0] == "Base image outdated"
        assert ev.config_source == ".github/workflows/ci.yml"

    def test_config_source_optional(self):
        ev = self._make()
        assert ev.config_source is None


# ---------------------------------------------------------------------------
# HistoricalEvidence
# ---------------------------------------------------------------------------


class TestHistoricalEvidence:
    def _make(self, **overrides) -> HistoricalEvidence:
        kwargs = {**base_kwargs(EvidenceType.HISTORICAL)}
        kwargs.update(overrides)
        return HistoricalEvidence(**kwargs)

    def test_valid_no_history(self):
        ev = self._make()
        assert ev.evidence_type == EvidenceType.HISTORICAL
        assert ev.similar_failures == []
        assert ev.recurrence_count == 0

    def test_valid_with_history(self):
        ev = self._make(
            similar_failures=[
                SimilarFailure(
                    run_id="run-20240108-007",
                    date=datetime(2024, 1, 8, tzinfo=timezone.utc),
                    root_cause="utility-lib 2.2.0 breaking change",
                    fix_applied="Pinned to 2.1.5",
                    similarity_score=0.92,
                )
            ],
            recurrence_count=2,
            last_seen=datetime(2024, 1, 8, tzinfo=timezone.utc),
            known_fix="Pin utility-lib to last compatible version",
        )
        assert ev.recurrence_count == 2
        assert ev.known_fix is not None
        assert len(ev.similar_failures) == 1

    def test_known_fix_optional(self):
        ev = self._make()
        assert ev.known_fix is None

    def test_negative_recurrence_rejected(self):
        with pytest.raises(ValidationError):
            self._make(recurrence_count=-1)


# ---------------------------------------------------------------------------
# JSON serialization round-trips
# ---------------------------------------------------------------------------


class TestJsonRoundTrip:
    """Every evidence model must survive model → JSON → model without data loss."""

    def _roundtrip(self, model):
        json_str = model.model_dump_json()
        data = json.loads(json_str)
        reconstructed = model.__class__.model_validate(data)
        assert reconstructed == model
        return reconstructed

    def test_failure_evidence_roundtrip(self):
        ev = FailureEvidence(
            **base_kwargs(EvidenceType.FAILURE),
            error_class="TypeError",
            error_message="formatCurrency is not a function",
            affected_stage="test",
            stack_trace=["at invoice.js:12"],
            failure_timestamp=datetime(2024, 3, 15, 14, 32, 16, tzinfo=timezone.utc),
        )
        self._roundtrip(ev)

    def test_change_evidence_roundtrip(self):
        ev = ChangeEvidence(
            **base_kwargs(EvidenceType.CHANGE),
            commit_sha="a1b2c3d4",
            changed_files=[ChangedFile(path="package.json", additions=1, deletions=1)],
        )
        self._roundtrip(ev)

    def test_dependency_evidence_roundtrip(self):
        ev = DependencyEvidence(
            **base_kwargs(EvidenceType.DEPENDENCY),
            changed=[DepChange(name="utility-lib", old_version="2.3.1", new_version="3.0.0")],
            breaking_changes=["formatCurrency removed"],
        )
        self._roundtrip(ev)

    def test_test_evidence_roundtrip(self):
        ev = TestEvidence(
            **base_kwargs(EvidenceType.TEST),
            failed_tests=[FailedTest(name="test_x", failure_message="boom")],
            total_run=10,
            total_failed=1,
        )
        self._roundtrip(ev)

    def test_infra_evidence_roundtrip(self):
        ev = InfraEvidence(
            **base_kwargs(EvidenceType.INFRA),
            dockerfile_issues=["stale base image"],
        )
        self._roundtrip(ev)

    def test_historical_evidence_roundtrip(self):
        ev = HistoricalEvidence(
            **base_kwargs(EvidenceType.HISTORICAL),
            similar_failures=[
                SimilarFailure(
                    run_id="r1",
                    date=datetime(2024, 1, 1, tzinfo=timezone.utc),
                    root_cause="dep bump",
                )
            ],
        )
        self._roundtrip(ev)

    def test_evidence_type_preserved_in_json(self):
        ev = TestEvidence(**base_kwargs(EvidenceType.TEST), total_run=5)
        data = json.loads(ev.model_dump_json())
        assert data["evidence_type"] == "test"

    def test_metadata_dict_preserved(self):
        ev = InfraEvidence(
            **base_kwargs(EvidenceType.INFRA),
            metadata={"raw_key": "raw_value", "count": 3},
        )
        rt = self._roundtrip(ev)
        assert rt.metadata["raw_key"] == "raw_value"
        assert rt.metadata["count"] == 3


# ---------------------------------------------------------------------------
# PipelineFailureEvent
# ---------------------------------------------------------------------------


class TestPipelineFailureEvent:
    def _make(self, **overrides) -> PipelineFailureEvent:
        kwargs = {
            "id": "evt-scenario-001",
            "repo": "acme/payments-service",
            "branch": "feature/update-deps",
            "commit_sha": "a1b2c3d4",
            "pipeline_run_id": "run-001",
            "timestamp": datetime(2024, 3, 15, 14, 32, 0, tzinfo=timezone.utc),
            "failure_stage": "test",
        }
        kwargs.update(overrides)
        return PipelineFailureEvent(**kwargs)

    def test_valid_minimal(self):
        ev = self._make()
        assert ev.repo == "acme/payments-service"
        assert ev.failure_stage == "test"
        assert ev.history == []

    def test_optional_raw_fields_default_none(self):
        ev = self._make()
        assert ev.raw_log_url is None
        assert ev.raw_log_text is None
        assert ev.git_diff_patch is None

    def test_with_history(self):
        from datetime import timezone

        ev = self._make(
            history=[
                HistoricalRun(
                    run_id="run-old",
                    date=datetime(2024, 1, 8, tzinfo=timezone.utc),
                    root_cause="dep issue",
                )
            ]
        )
        assert len(ev.history) == 1
        assert ev.history[0].run_id == "run-old"

    def test_matches_sample_json_shape(self):
        """The sample failure_event.json must parse cleanly into PipelineFailureEvent."""
        import json
        import pathlib

        sample_path = (
            pathlib.Path(__file__).parent.parent.parent
            / "sample-data"
            / "scenario-001"
            / "failure_event.json"
        )
        if not sample_path.exists():
            pytest.skip("sample data not found relative to test location")
        data = json.loads(sample_path.read_text())
        ev = PipelineFailureEvent(**data)
        assert ev.id == "evt-scenario-001"

    def test_id_required(self):
        kwargs = {
            "repo": "x",
            "branch": "main",
            "commit_sha": "abc",
            "pipeline_run_id": "r1",
            "timestamp": datetime.utcnow(),
            "failure_stage": "test",
        }
        with pytest.raises(ValidationError):
            PipelineFailureEvent(**kwargs)  # missing id

    def test_roundtrip(self):
        ev = self._make(raw_log_text="BUILD FAILED")
        data = json.loads(ev.model_dump_json())
        rt = PipelineFailureEvent.model_validate(data)
        assert rt == ev
