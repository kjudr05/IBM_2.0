"""
PipelineFailureEvent — the ingest payload for a CI/CD pipeline failure.

This is the raw input that arrives at POST /api/ingest (or is loaded from
sample-data/). All investigation agents receive this object as their input.

The shape must match sample-data/scenario-001/failure_event.json exactly.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class HistoricalRun(BaseModel):
    """Summary of a previous CI run stored in the failure event payload."""

    run_id: str
    date: datetime
    failure_stage: str | None = None
    root_cause: str | None = None
    fix_applied: str | None = None
    resolved_in: str | None = None

    model_config = {"frozen": True}


class PipelineFailureEvent(BaseModel):
    """
    Ingest schema for a CI/CD pipeline failure.

    Produced by the webhook handler or sample-data loader and passed directly
    to the Bob Orchestrator, which distributes it to each investigator.

    All text fields that carry raw file content are plain strings — callers are
    responsible for reading file content before constructing this model.
    """

    id: str = Field(description="Unique event identifier (uuid or run-scoped string)")
    repo: str = Field(description="Repository slug, e.g. 'acme/payments-service'")
    branch: str
    commit_sha: str
    pipeline_run_id: str
    timestamp: datetime = Field(description="UTC timestamp of the pipeline failure")
    failure_stage: str = Field(
        description="CI stage that failed, e.g. 'test', 'build', 'deploy'"
    )

    # Raw source data — passed as strings so investigators can parse them
    raw_log_url: str | None = Field(
        default=None,
        description="URL to the full CI log (used when raw_log_text is not embedded)",
    )
    raw_log_text: str | None = Field(
        default=None, description="Full CI log text (embedded)"
    )
    git_diff_patch: str | None = Field(
        default=None, description="Unified diff of the triggering commit"
    )
    test_results_xml: str | None = Field(
        default=None, description="JUnit-compatible XML test results"
    )
    dependency_before: dict = Field(
        default_factory=dict,
        description="Dependency manifest (package.json, requirements.txt parsed to dict) BEFORE the commit",
    )
    dependency_after: dict = Field(
        default_factory=dict,
        description="Dependency manifest AFTER the commit",
    )
    dockerfile_content: str | None = Field(
        default=None, description="Contents of the Dockerfile"
    )
    ci_config_content: str | None = Field(
        default=None, description="Contents of the CI configuration file"
    )
    history: list[HistoricalRun] = Field(
        default_factory=list,
        description="Previous CI runs for this repository (for the History Investigator)",
    )

    model_config = {"frozen": True}
