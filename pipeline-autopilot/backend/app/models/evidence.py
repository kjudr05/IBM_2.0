"""
Evidence artifact schemas for Pipeline Autopilot.

All investigation agents return typed subclasses of BaseEvidence.
Evidence models represent observations from a data source — not AI reasoning,
not UI state, and not provider-specific formats.

Hierarchy:
    BaseEvidence
    ├── FailureEvidence      (log investigator)
    ├── ChangeEvidence       (code investigator)
    ├── DependencyEvidence   (dependency investigator)
    ├── TestEvidence         (test investigator)
    ├── InfraEvidence        (infrastructure investigator)
    └── HistoricalEvidence   (history investigator)

Supporting value objects (used inside the above):
    EvidenceSource     — provenance: which agent produced this, from which input
    ChangedFile        — one modified file in a commit
    DepChange          — one dependency version change
    FailedTest         — one failed test case
    SimilarFailure     — one historical failure record
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Annotated, Any

from pydantic import BaseModel, Field, field_validator, model_validator


# ---------------------------------------------------------------------------
# Bounded enumerations
# ---------------------------------------------------------------------------


class EvidenceType(str, Enum):
    """Discriminator for the six evidence kinds."""

    FAILURE = "failure"
    CHANGE = "change"
    DEPENDENCY = "dependency"
    TEST = "test"
    INFRA = "infra"
    HISTORICAL = "historical"


class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class TestCaseStatus(str, Enum):
    FAILED = "failed"
    PASSED = "passed"
    SKIPPED = "skipped"
    ERROR = "error"


# ---------------------------------------------------------------------------
# Confidence — reusable annotated type
# ---------------------------------------------------------------------------

Confidence = Annotated[float, Field(ge=0.0, le=1.0)]


# ---------------------------------------------------------------------------
# Supporting value objects
# ---------------------------------------------------------------------------


class EvidenceSource(BaseModel):
    """Provenance record: where this evidence came from."""

    agent_id: str = Field(description="ID of the investigator agent that produced this evidence")
    input_file: str | None = Field(
        default=None,
        description="File or data source the agent read (e.g. 'ci_log.txt', 'git_diff.patch')",
    )
    extraction_method: str | None = Field(
        default=None,
        description="How the evidence was extracted (e.g. 'regex_parse', 'xml_parse', 'mock')",
    )

    model_config = {"frozen": True}


class ChangedFile(BaseModel):
    """One file modified in a commit."""

    path: str
    additions: int = Field(default=0, ge=0)
    deletions: int = Field(default=0, ge=0)
    diff_hunk: str | None = None

    model_config = {"frozen": True}


class DepChange(BaseModel):
    """One dependency whose version changed between two manifests."""

    name: str
    old_version: str | None = Field(default=None, description="None if the dependency was added")
    new_version: str | None = Field(default=None, description="None if the dependency was removed")
    affected_component: str | None = None

    model_config = {"frozen": True}

    @model_validator(mode="after")
    def at_least_one_version(self) -> "DepChange":
        if self.old_version is None and self.new_version is None:
            raise ValueError("DepChange must have at least one of old_version or new_version")
        return self


class FailedTest(BaseModel):
    """One failing test case."""

    name: str
    class_name: str | None = None
    failure_message: str | None = None
    duration_ms: float | None = Field(default=None, ge=0)

    model_config = {"frozen": True}


class SimilarFailure(BaseModel):
    """A historical failure that resembles the current one."""

    run_id: str
    date: datetime
    root_cause: str
    fix_applied: str | None = None
    similarity_score: Confidence | None = None

    model_config = {"frozen": True}


# ---------------------------------------------------------------------------
# Base evidence
# ---------------------------------------------------------------------------


class BaseEvidence(BaseModel):
    """
    Root class for all evidence artifacts.

    Every piece of evidence carries:
    - identity (evidence_id, pipeline_id)
    - provenance (source)
    - a discrimination tag (evidence_type)
    - a plain-language one-liner (summary)
    - a confidence score in [0, 1]
    - creation timestamp
    - an open metadata dict for agent-specific extras that don't yet have a
      first-class field (kept small on purpose)
    """

    evidence_id: str = Field(description="Unique identifier for this evidence artifact")
    pipeline_id: str = Field(description="The pipeline run this evidence belongs to")
    evidence_type: EvidenceType
    source: EvidenceSource
    summary: str = Field(
        description="Plain-language one-liner suitable for display to a non-technical user"
    )
    confidence: Confidence = Field(
        description="Agent's confidence that this evidence is accurate (0.0–1.0)"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="UTC timestamp when the evidence was produced",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Agent-specific extras that don't fit a first-class field",
    )

    model_config = {"frozen": True}


# ---------------------------------------------------------------------------
# FailureEvidence
# ---------------------------------------------------------------------------


class FailureEvidence(BaseEvidence):
    """
    Evidence produced by the Log Investigator.

    Captures the observable CI/CD failure: error class, message, stack trace,
    which pipeline stage failed, and the raw log excerpt surrounding the error.
    """

    evidence_type: EvidenceType = EvidenceType.FAILURE

    error_class: str = Field(description="Exception/error class name, e.g. 'TypeError'")
    error_message: str = Field(description="Full error message text")
    stack_trace: list[str] = Field(
        default_factory=list,
        description="Stack trace lines, outermost first",
    )
    affected_stage: str = Field(
        description="CI stage where the failure occurred, e.g. 'test', 'build', 'deploy'"
    )
    failure_timestamp: datetime | None = Field(
        default=None,
        description="Timestamp of the failure as recorded in the log (if parseable)",
    )
    severity: Severity = Field(default=Severity.HIGH)
    log_excerpt: str | None = Field(
        default=None,
        description="Raw log lines surrounding the failure (trimmed)",
    )
    file_path: str | None = Field(
        default=None, description="Source file implicated by the stack trace"
    )
    line_number: int | None = Field(default=None, ge=1)


# ---------------------------------------------------------------------------
# ChangeEvidence
# ---------------------------------------------------------------------------


class ChangeEvidence(BaseEvidence):
    """
    Evidence produced by the Code Investigator.

    Captures what changed in the commit that triggered the pipeline run:
    changed files, changed function names, diff hunks, commit metadata.
    """

    evidence_type: EvidenceType = EvidenceType.CHANGE

    commit_sha: str
    author: str | None = None
    commit_message: str | None = None
    commit_timestamp: datetime | None = None
    changed_files: list[ChangedFile] = Field(default_factory=list)
    changed_functions: list[str] = Field(
        default_factory=list,
        description="Function/method names that were modified",
    )
    total_additions: int = Field(default=0, ge=0)
    total_deletions: int = Field(default=0, ge=0)


# ---------------------------------------------------------------------------
# DependencyEvidence
# ---------------------------------------------------------------------------


class DependencyEvidence(BaseEvidence):
    """
    Evidence produced by the Dependency Investigator.

    Captures differences between the before/after dependency manifests and
    identifies any known breaking changes.
    """

    evidence_type: EvidenceType = EvidenceType.DEPENDENCY

    added: list[DepChange] = Field(default_factory=list)
    removed: list[DepChange] = Field(default_factory=list)
    changed: list[DepChange] = Field(default_factory=list)
    breaking_changes: list[str] = Field(
        default_factory=list,
        description="Human-readable descriptions of identified incompatibilities",
    )

    @field_validator("added", "removed", "changed", mode="before")
    @classmethod
    def coerce_dep_changes(cls, v: Any) -> list:
        # Accept plain dicts in addition to DepChange instances
        return v if v is not None else []


# ---------------------------------------------------------------------------
# TestEvidence
# ---------------------------------------------------------------------------


class TestRunEvidence(BaseEvidence):
    """
    Evidence produced by the Test Investigator.

    Captures which tests failed, which were previously passing (regressions),
    and overall run statistics.
    """

    evidence_type: EvidenceType = EvidenceType.TEST

    failed_tests: list[FailedTest] = Field(default_factory=list)
    flaky_tests: list[str] = Field(
        default_factory=list,
        description="Test names known to be non-deterministic in prior runs",
    )
    regression_tests: list[str] = Field(
        default_factory=list,
        description="Test names that passed in the most recent prior run but fail now",
    )
    total_run: int = Field(default=0, ge=0)
    total_failed: int = Field(default=0, ge=0)
    total_passed: int = Field(default=0, ge=0)
    total_skipped: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def failed_count_consistent(self) -> "TestRunEvidence":
        if self.total_failed > self.total_run and self.total_run > 0:
            raise ValueError("total_failed cannot exceed total_run")
        return self


# ---------------------------------------------------------------------------
# InfraEvidence
# ---------------------------------------------------------------------------


class InfraEvidence(BaseEvidence):
    """
    Evidence produced by the Infrastructure Investigator.

    Captures issues found in Dockerfile, CI configuration, environment
    variables, and base image references.
    """

    evidence_type: EvidenceType = EvidenceType.INFRA

    dockerfile_issues: list[str] = Field(default_factory=list)
    ci_config_issues: list[str] = Field(default_factory=list)
    env_var_issues: list[str] = Field(default_factory=list)
    image_changes: list[str] = Field(
        default_factory=list,
        description="Base image changes detected between runs",
    )
    config_source: str | None = Field(
        default=None,
        description="Primary configuration file examined (e.g. '.github/workflows/ci.yml')",
    )


# ---------------------------------------------------------------------------
# HistoricalEvidence
# ---------------------------------------------------------------------------


class HistoricalEvidence(BaseEvidence):
    """
    Evidence produced by the History Investigator.

    Captures similar past failures, their resolutions, and how many times
    this pattern has recurred.
    """

    evidence_type: EvidenceType = EvidenceType.HISTORICAL

    similar_failures: list[SimilarFailure] = Field(default_factory=list)
    recurrence_count: int = Field(
        default=0,
        ge=0,
        description="How many times a similar failure has been seen before",
    )
    last_seen: datetime | None = Field(
        default=None,
        description="Most recent prior occurrence of a similar failure",
    )
    known_fix: str | None = Field(
        default=None,
        description="Fix that resolved the most similar prior failure (if available)",
    )


# ---------------------------------------------------------------------------
# Union type — used by orchestrator to hold any evidence artifact
# ---------------------------------------------------------------------------

AnyEvidence = (
    FailureEvidence
    | ChangeEvidence
    | DependencyEvidence
    | TestRunEvidence
    | InfraEvidence
    | HistoricalEvidence
)

# Backward-compatible alias — prefer TestRunEvidence in new code
TestEvidence = TestRunEvidence
