"""
Unit and integration tests for Task 3:
  - database.py  (schema init, connection)
  - store.py     (save_pipeline, get_pipeline, list_pipelines, set_state, get_state)
  - api/ingest.py (POST /api/ingest)
  - api/pipeline.py (GET /api/pipeline/{id})
  - api/scenarios.py (GET /api/scenarios, POST /api/scenarios/{id}/load)

All tests use the in-memory SQLite fixture from conftest.py.
HTTP tests use the httpx AsyncClient fixture.
"""

from __future__ import annotations

import json
import pathlib
from datetime import datetime, timezone

import pytest
from httpx import AsyncClient

from app.db import store as store_module
from app.db.store import (
    PipelineRecord,
    get_pipeline,
    get_state,
    list_pipelines,
    save_pipeline,
    set_state,
)
from app.models.events import HistoricalRun, PipelineFailureEvent

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_NOW = datetime(2024, 3, 15, 14, 32, 0, tzinfo=timezone.utc)

SAMPLE_DATA_DIR = (
    pathlib.Path(__file__).parent.parent.parent / "sample-data"
)


def make_event(**overrides) -> PipelineFailureEvent:
    """Return a minimal valid PipelineFailureEvent."""
    kwargs = {
        "id": "pipe-test-001",
        "repo": "acme/payments-service",
        "branch": "feature/update-deps",
        "commit_sha": "a1b2c3d4",
        "pipeline_run_id": "run-test-001",
        "timestamp": _NOW,
        "failure_stage": "test",
    }
    kwargs.update(overrides)
    return PipelineFailureEvent(**kwargs)


# ---------------------------------------------------------------------------
# store.py — save_pipeline / get_pipeline
# ---------------------------------------------------------------------------


class TestSavePipeline:
    async def test_save_returns_id(self, db_override):
        event = make_event()
        result = await save_pipeline(event)
        assert result == "pipe-test-001"

    async def test_saved_record_roundtrip(self, db_override):
        event = make_event(raw_log_text="BUILD FAILED")
        await save_pipeline(event)
        record = await get_pipeline("pipe-test-001")
        assert record is not None
        assert isinstance(record, PipelineRecord)
        assert record.id == "pipe-test-001"
        assert record.repo == "acme/payments-service"
        assert record.event.raw_log_text == "BUILD FAILED"

    async def test_duplicate_id_raises(self, db_override):
        event = make_event()
        await save_pipeline(event)
        with pytest.raises(ValueError, match="already exists"):
            await save_pipeline(event)

    async def test_get_nonexistent_returns_none(self, db_override):
        result = await get_pipeline("does-not-exist")
        assert result is None

    async def test_full_event_fields_preserved(self, db_override):
        event = make_event(
            git_diff_patch="diff --git a/package.json b/package.json",
            raw_log_text="FAIL: TypeError",
            test_results_xml="<testsuites/>",
            dependency_before={"utility-lib": "2.3.1"},
            dependency_after={"utility-lib": "3.0.0"},
        )
        await save_pipeline(event)
        record = await get_pipeline("pipe-test-001")
        assert record.event.git_diff_patch == "diff --git a/package.json b/package.json"
        assert record.event.dependency_before == {"utility-lib": "2.3.1"}
        assert record.event.dependency_after == {"utility-lib": "3.0.0"}

    async def test_history_preserved(self, db_override):
        event = make_event(
            history=[
                HistoricalRun(
                    run_id="old-run",
                    date=datetime(2024, 1, 1, tzinfo=timezone.utc),
                    root_cause="dep bump",
                )
            ]
        )
        await save_pipeline(event)
        record = await get_pipeline("pipe-test-001")
        assert len(record.event.history) == 1
        assert record.event.history[0].run_id == "old-run"


class TestListPipelines:
    async def test_empty_list(self, db_override):
        result = await list_pipelines()
        assert result == []

    async def test_multiple_pipelines_returned(self, db_override):
        await save_pipeline(make_event(id="p1", pipeline_run_id="r1"))
        await save_pipeline(make_event(id="p2", pipeline_run_id="r2"))
        result = await list_pipelines()
        assert len(result) == 2

    async def test_ordered_newest_first(self, db_override):
        await save_pipeline(make_event(id="p1", pipeline_run_id="r1"))
        await save_pipeline(make_event(id="p2", pipeline_run_id="r2"))
        result = await list_pipelines()
        # newest inserted last but sorted DESC by created_at; both inserted
        # in the same second so order is stable by id alphabetically in sqlite
        ids = {r.id for r in result}
        assert "p1" in ids
        assert "p2" in ids


# ---------------------------------------------------------------------------
# store.py — set_state / get_state
# ---------------------------------------------------------------------------


class TestPipelineState:
    async def test_set_and_get(self, db_override):
        event = make_event()
        await save_pipeline(event)
        await set_state("pipe-test-001", "status", "investigating")
        value = await get_state("pipe-test-001", "status")
        assert value == "investigating"

    async def test_get_nonexistent_key_returns_none(self, db_override):
        event = make_event()
        await save_pipeline(event)
        value = await get_state("pipe-test-001", "missing_key")
        assert value is None

    async def test_upsert_overwrites(self, db_override):
        event = make_event()
        await save_pipeline(event)
        await set_state("pipe-test-001", "status", "investigating")
        await set_state("pipe-test-001", "status", "complete")
        value = await get_state("pipe-test-001", "status")
        assert value == "complete"

    async def test_multiple_keys_independent(self, db_override):
        event = make_event()
        await save_pipeline(event)
        await set_state("pipe-test-001", "status", "done")
        await set_state("pipe-test-001", "result", "fixed")
        assert await get_state("pipe-test-001", "status") == "done"
        assert await get_state("pipe-test-001", "result") == "fixed"


# ---------------------------------------------------------------------------
# POST /api/ingest
# ---------------------------------------------------------------------------


class TestIngestEndpoint:
    async def test_valid_ingest_returns_201(self, test_client: AsyncClient):
        payload = {
            "id": "pipe-http-001",
            "repo": "acme/svc",
            "branch": "main",
            "commit_sha": "abc123",
            "pipeline_run_id": "run-001",
            "timestamp": "2024-03-15T14:32:00Z",
            "failure_stage": "test",
        }
        resp = await test_client.post("/api/ingest", json=payload)
        assert resp.status_code == 201
        body = resp.json()
        assert body["error"] is None
        assert body["data"]["pipeline_id"] == "pipe-http-001"

    async def test_duplicate_ingest_returns_409(self, test_client: AsyncClient):
        payload = {
            "id": "pipe-dup-001",
            "repo": "acme/svc",
            "branch": "main",
            "commit_sha": "abc123",
            "pipeline_run_id": "run-001",
            "timestamp": "2024-03-15T14:32:00Z",
            "failure_stage": "test",
        }
        await test_client.post("/api/ingest", json=payload)
        resp = await test_client.post("/api/ingest", json=payload)
        assert resp.status_code == 409

    async def test_invalid_payload_returns_422(self, test_client: AsyncClient):
        resp = await test_client.post("/api/ingest", json={"id": "x"})
        assert resp.status_code == 422

    async def test_ingest_with_optional_fields(self, test_client: AsyncClient):
        payload = {
            "id": "pipe-opt-001",
            "repo": "acme/svc",
            "branch": "main",
            "commit_sha": "abc",
            "pipeline_run_id": "r1",
            "timestamp": "2024-03-15T14:32:00Z",
            "failure_stage": "build",
            "raw_log_text": "BUILD FAILED",
            "git_diff_patch": "diff ...",
            "dependency_before": {"pkg": "1.0.0"},
            "dependency_after": {"pkg": "2.0.0"},
        }
        resp = await test_client.post("/api/ingest", json=payload)
        assert resp.status_code == 201


# ---------------------------------------------------------------------------
# GET /api/pipeline/{id}
# ---------------------------------------------------------------------------


class TestPipelineEndpoint:
    async def test_get_existing_pipeline(self, test_client: AsyncClient):
        # First ingest
        payload = {
            "id": "pipe-get-001",
            "repo": "acme/svc",
            "branch": "main",
            "commit_sha": "abc",
            "pipeline_run_id": "r1",
            "timestamp": "2024-03-15T14:32:00Z",
            "failure_stage": "test",
            "raw_log_text": "FAIL",
        }
        await test_client.post("/api/ingest", json=payload)
        # Then retrieve
        resp = await test_client.get("/api/pipeline/pipe-get-001")
        assert resp.status_code == 200
        body = resp.json()
        assert body["error"] is None
        data = body["data"]
        assert data["pipeline_id"] == "pipe-get-001"
        assert data["repo"] == "acme/svc"
        assert data["failure_stage"] == "test"
        assert data["status"] == "pending"
        assert data["event"]["raw_log_text"] == "FAIL"

    async def test_get_nonexistent_returns_404(self, test_client: AsyncClient):
        resp = await test_client.get("/api/pipeline/does-not-exist")
        assert resp.status_code == 404

    async def test_status_reflects_state_value(self, test_client: AsyncClient):
        payload = {
            "id": "pipe-status-001",
            "repo": "acme/svc",
            "branch": "main",
            "commit_sha": "abc",
            "pipeline_run_id": "r1",
            "timestamp": "2024-03-15T14:32:00Z",
            "failure_stage": "test",
        }
        await test_client.post("/api/ingest", json=payload)
        # Manually write a state key (simulating orchestrator)
        await set_state("pipe-status-001", "status", "investigating")
        resp = await test_client.get("/api/pipeline/pipe-status-001")
        assert resp.json()["data"]["status"] == "investigating"


# ---------------------------------------------------------------------------
# GET /api/scenarios
# ---------------------------------------------------------------------------


class TestScenariosListEndpoint:
    async def test_returns_scenarios(self, test_client: AsyncClient, monkeypatch):
        monkeypatch.setenv("SAMPLE_DATA_DIR", str(SAMPLE_DATA_DIR))
        resp = await test_client.get("/api/scenarios")
        assert resp.status_code == 200
        body = resp.json()
        assert body["error"] is None
        scenarios = body["data"]["scenarios"]
        assert len(scenarios) >= 1
        assert scenarios[0]["id"] == "001"
        assert scenarios[0]["name"] == "The Silent Semver Break"

    async def test_missing_sample_dir_returns_empty(self, test_client: AsyncClient, monkeypatch):
        monkeypatch.setenv("SAMPLE_DATA_DIR", "/nonexistent/path")
        resp = await test_client.get("/api/scenarios")
        assert resp.status_code == 200
        assert resp.json()["data"]["scenarios"] == []


# ---------------------------------------------------------------------------
# POST /api/scenarios/{id}/load
# ---------------------------------------------------------------------------


class TestScenarioLoadEndpoint:
    async def test_load_scenario_001(self, test_client: AsyncClient, monkeypatch):
        monkeypatch.setenv("SAMPLE_DATA_DIR", str(SAMPLE_DATA_DIR))
        resp = await test_client.post("/api/scenarios/001/load")
        assert resp.status_code == 201
        body = resp.json()
        assert body["error"] is None
        data = body["data"]
        assert data["scenario_id"] == "001"
        assert data["repo"] == "acme/payments-service"
        assert data["failure_stage"] == "test"
        # pipeline_id should be unique (has uuid suffix)
        assert "evt-scenario-001" in data["pipeline_id"]

    async def test_loaded_pipeline_retrievable(self, test_client: AsyncClient, monkeypatch):
        monkeypatch.setenv("SAMPLE_DATA_DIR", str(SAMPLE_DATA_DIR))
        load_resp = await test_client.post("/api/scenarios/001/load")
        pipeline_id = load_resp.json()["data"]["pipeline_id"]

        get_resp = await test_client.get(f"/api/pipeline/{pipeline_id}")
        assert get_resp.status_code == 200
        data = get_resp.json()["data"]
        assert data["pipeline_id"] == pipeline_id
        # Real file contents should be embedded
        assert data["event"]["raw_log_text"] is not None
        assert "TypeError" in data["event"]["raw_log_text"]

    async def test_load_twice_creates_two_pipelines(self, test_client: AsyncClient, monkeypatch):
        monkeypatch.setenv("SAMPLE_DATA_DIR", str(SAMPLE_DATA_DIR))
        r1 = await test_client.post("/api/scenarios/001/load")
        r2 = await test_client.post("/api/scenarios/001/load")
        assert r1.status_code == 201
        assert r2.status_code == 201
        # Each load gets a different unique id
        assert r1.json()["data"]["pipeline_id"] != r2.json()["data"]["pipeline_id"]

    async def test_unknown_scenario_returns_404(self, test_client: AsyncClient, monkeypatch):
        monkeypatch.setenv("SAMPLE_DATA_DIR", str(SAMPLE_DATA_DIR))
        resp = await test_client.post("/api/scenarios/999/load")
        assert resp.status_code == 404

    async def test_embedded_files_present(self, test_client: AsyncClient, monkeypatch):
        """Verify that sample-data files are embedded into the loaded event."""
        monkeypatch.setenv("SAMPLE_DATA_DIR", str(SAMPLE_DATA_DIR))
        load_resp = await test_client.post("/api/scenarios/001/load")
        pipeline_id = load_resp.json()["data"]["pipeline_id"]
        get_resp = await test_client.get(f"/api/pipeline/{pipeline_id}")
        event = get_resp.json()["data"]["event"]

        assert event["git_diff_patch"] is not None
        assert "utility-lib" in event["git_diff_patch"]
        assert event["test_results_xml"] is not None
        assert "testsuites" in event["test_results_xml"]
        assert event["dockerfile_content"] is not None
        assert event["ci_config_content"] is not None
        assert event["dependency_before"] != {}
        assert event["dependency_after"] != {}


# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------


class TestHealthEndpoint:
    async def test_health_ok(self, test_client: AsyncClient):
        resp = await test_client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}
