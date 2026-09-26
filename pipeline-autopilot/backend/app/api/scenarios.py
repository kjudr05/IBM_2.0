"""
Scenarios router — sample-data management endpoints.

GET  /api/scenarios          — list available sample scenarios
POST /api/scenarios/{id}/load — load a scenario as a new pipeline run

The loader reads all source files from sample-data/scenario-{id}/ and
builds a complete PipelineFailureEvent, then delegates to save_pipeline().

Sample-data directory resolution order:
  1. SAMPLE_DATA_DIR environment variable
  2. <repo-root>/sample-data/  (relative to this file's location)
"""

from __future__ import annotations

import json
import os
import pathlib
import uuid

from fastapi import APIRouter, HTTPException, status

from app.db.store import list_pipelines, save_pipeline
from app.models.events import HistoricalRun, PipelineFailureEvent

router = APIRouter(tags=["scenarios"])

# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

_REPO_ROOT = pathlib.Path(__file__).parent.parent.parent.parent
_DEFAULT_SAMPLE_DIR = _REPO_ROOT / "sample-data"


def _sample_dir() -> pathlib.Path:
    return pathlib.Path(os.environ.get("SAMPLE_DATA_DIR", str(_DEFAULT_SAMPLE_DIR)))


def _read_text(path: pathlib.Path) -> str | None:
    """Read a file as text; return None if the file does not exist."""
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None


# ---------------------------------------------------------------------------
# GET /api/scenarios
# ---------------------------------------------------------------------------


@router.get("/scenarios")
async def list_scenarios() -> dict:
    """Return the index of available sample scenarios."""
    index_path = _sample_dir() / "scenarios.json"
    if not index_path.exists():
        return {"data": {"scenarios": []}, "error": None}

    data = json.loads(index_path.read_text(encoding="utf-8"))

    # Annotate each scenario with how many pipeline runs exist for it
    runs = await list_pipelines()
    run_counts: dict[str, int] = {}
    for run in runs:
        # scenario id is embedded in the pipeline_run_id prefix
        for scenario in data.get("scenarios", []):
            prefix = f"scenario-{scenario['id']}"
            if prefix in run.pipeline_run_id or prefix in run.id:
                run_counts[scenario["id"]] = run_counts.get(scenario["id"], 0) + 1

    for scenario in data.get("scenarios", []):
        scenario["run_count"] = run_counts.get(scenario["id"], 0)

    return {"data": data, "error": None}


# ---------------------------------------------------------------------------
# POST /api/scenarios/{id}/load
# ---------------------------------------------------------------------------


@router.post("/scenarios/{scenario_id}/load", status_code=status.HTTP_201_CREATED)
async def load_scenario(scenario_id: str) -> dict:
    """
    Load a sample scenario as a new PipelineFailureEvent and persist it.

    Reads the scenario source files, embeds their content into the event,
    generates a unique pipeline id (to allow repeated loads for benchmarking),
    and stores the event.

    Returns the new pipeline_id.
    """
    scenario_dir = _sample_dir() / f"scenario-{scenario_id}"
    if not scenario_dir.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scenario '{scenario_id}' not found at {scenario_dir}",
        )

    # --- Read base event JSON ---
    event_path = scenario_dir / "failure_event.json"
    if not event_path.exists():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"failure_event.json missing from scenario '{scenario_id}'",
        )
    event_data = json.loads(event_path.read_text(encoding="utf-8"))

    # --- Embed real file contents, overriding the placeholder strings ---
    ci_log = _read_text(scenario_dir / "ci_log.txt")
    if ci_log:
        event_data["raw_log_text"] = ci_log

    git_diff = _read_text(scenario_dir / "git_diff.patch")
    if git_diff:
        event_data["git_diff_patch"] = git_diff

    test_xml = _read_text(scenario_dir / "test_results.xml")
    if test_xml:
        event_data["test_results_xml"] = test_xml

    dockerfile = _read_text(scenario_dir / "dockerfile.txt")
    if dockerfile:
        event_data["dockerfile_content"] = dockerfile

    ci_config = _read_text(scenario_dir / "ci_config.yml")
    if ci_config:
        event_data["ci_config_content"] = ci_config

    dep_before_path = scenario_dir / "dependency_before.json"
    if dep_before_path.exists():
        event_data["dependency_before"] = json.loads(
            dep_before_path.read_text(encoding="utf-8")
        )

    dep_after_path = scenario_dir / "dependency_after.json"
    if dep_after_path.exists():
        event_data["dependency_after"] = json.loads(
            dep_after_path.read_text(encoding="utf-8")
        )

    history_path = scenario_dir / "history.json"
    if history_path.exists():
        event_data["history"] = json.loads(history_path.read_text(encoding="utf-8"))

    # --- Generate a unique pipeline id so the same scenario can be loaded
    #     multiple times (useful for benchmarking). The base event id is used
    #     as a prefix so it remains traceable to the scenario. ---
    base_id = event_data.get("id", f"scenario-{scenario_id}")
    unique_id = f"{base_id}-{uuid.uuid4().hex[:8]}"
    event_data["id"] = unique_id

    # --- Validate and persist ---
    try:
        event = PipelineFailureEvent(**event_data)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Failed to build PipelineFailureEvent: {exc}",
        ) from exc

    try:
        pipeline_id = await save_pipeline(event)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    return {
        "data": {
            "pipeline_id": pipeline_id,
            "scenario_id": scenario_id,
            "repo": event.repo,
            "branch": event.branch,
            "commit_sha": event.commit_sha,
            "failure_stage": event.failure_stage,
        },
        "error": None,
    }
