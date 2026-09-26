"""
Tests: SSE stream endpoint — all 12 events flow in correct order.

Task 9 test coverage:
1. Stream returns 200 with text/event-stream content type
2. All expected event types appear in the stream
3. Events appear in the correct order
4. EVIDENCE_ARRIVED fires once per investigator (×6)
5. CAUSAL_CHAIN event carries a chain with a root_cause_node_id
6. FIX_PROPOSED event carries a fix with confidence > 0
7. VALIDATION_RESULT event carries PASSED status for scenario-001
8. REPORT_READY event carries a report_id
9. STATE_TRANSITION states appear in the correct order
10. GET /api/report/{id} returns the full RecoveryReport after stream completes
11. GET /api/stream/{id} returns 404 for unknown pipeline
12. GET /api/report/{id} returns 404 for unknown pipeline
13. GET /api/report/{id} returns 202 when pipeline exists but stream not run yet
14. Counterfactual before/after state included in report
"""

from __future__ import annotations

import json
from typing import List

import pytest
import pytest_asyncio

from tests.backend.conftest import *  # noqa: F401,F403  (imports db_override + test_client)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SCENARIO_EVENT = {
    "id": "test-sse-pipeline-001",
    "repo": "acme/payments-service",
    "branch": "feature/update-deps",
    "commit_sha": "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2",
    "pipeline_run_id": "scenario-001-run-sse-test",
    "timestamp": "2024-03-15T14:32:00Z",
    "failure_stage": "test",
    "raw_log_text": (
        "[14:32:16] FAIL src/payments/invoice.test.js\n"
        "TypeError: formatCurrency is not a function\n"
        "[14:32:16] Tests: 3 failed, 14 passed, 17 total\n"
        "[14:32:16] BUILD FAILED"
    ),
    "git_diff_patch": (
        "diff --git a/package.json b/package.json\n"
        "@@ -5,7 +5,7 @@\n"
        '-    \"utility-lib\": \"^2.3.1\",\n'
        '+    \"utility-lib\": \"^3.0.0\",\n'
    ),
    "test_results_xml": (
        '<?xml version="1.0"?>'
        '<testsuite name="PaymentsService" tests="17" failures="3">'
        '<testcase name="test_format_invoice" classname="PaymentsService">'
        "<failure>TypeError: formatCurrency is not a function</failure>"
        "</testcase>"
        "</testsuite>"
    ),
    "dependency_before": {"dependencies": {"utility-lib": "^2.3.1"}},
    "dependency_after": {"dependencies": {"utility-lib": "^3.0.0"}},
}


def _parse_sse_events(raw_body: str) -> List[dict]:
    """Parse SSE stream body into a list of event dicts."""
    events = []
    for line in raw_body.splitlines():
        line = line.strip()
        if line.startswith("data: "):
            payload = line[len("data: "):]
            try:
                events.append(json.loads(payload))
            except json.JSONDecodeError:
                pass
    return events


async def _ingest_and_stream(test_client) -> tuple[str, List[dict]]:
    """
    Helper: ingest the test scenario event, open the SSE stream, collect all
    events, and return (pipeline_id, events_list).
    """
    # Ingest
    resp = await test_client.post("/api/ingest", json=_SCENARIO_EVENT)
    assert resp.status_code == 201, resp.text
    pipeline_id = resp.json()["data"]["pipeline_id"]

    # Open SSE stream — httpx collects the full body
    stream_resp = await test_client.get(f"/api/stream/{pipeline_id}")
    assert stream_resp.status_code == 200, stream_resp.text

    events = _parse_sse_events(stream_resp.text)
    return pipeline_id, events


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stream_returns_200_event_stream(test_client):
    """SSE endpoint returns HTTP 200 with text/event-stream content-type."""
    resp = await test_client.post("/api/ingest", json=_SCENARIO_EVENT)
    pipeline_id = resp.json()["data"]["pipeline_id"]

    stream_resp = await test_client.get(f"/api/stream/{pipeline_id}")
    assert stream_resp.status_code == 200
    assert "text/event-stream" in stream_resp.headers.get("content-type", "")


@pytest.mark.asyncio
async def test_stream_contains_all_required_event_types(test_client):
    """All required SSE event types appear in the stream."""
    _, events = await _ingest_and_stream(test_client)
    event_types = {e["type"] for e in events}

    required = {
        "STATE_TRANSITION",
        "EVIDENCE_ARRIVED",
        "CAUSAL_CHAIN",
        "FIX_PROPOSED",
        "VALIDATION_RESULT",
        "REPORT_READY",
    }
    for req in required:
        assert req in event_types, f"Missing event type: {req}"


@pytest.mark.asyncio
async def test_stream_no_error_events(test_client):
    """No ERROR event is emitted for scenario-001 (happy path)."""
    _, events = await _ingest_and_stream(test_client)
    error_events = [e for e in events if e["type"] == "ERROR"]
    assert error_events == [], f"Unexpected ERROR events: {error_events}"


@pytest.mark.asyncio
async def test_stream_state_transitions_in_correct_order(test_client):
    """STATE_TRANSITION states appear in the correct story order."""
    _, events = await _ingest_and_stream(test_client)
    state_events = [e for e in events if e["type"] == "STATE_TRANSITION"]
    states = [e["state"] for e in state_events]

    expected_order = [
        "AGENTS_ACTIVATING",
        "EVIDENCE_CONVERGING",
        "ROOT_CAUSE_IDENTIFIED",
        "COUNTERFACTUAL_SIMULATING",
        "SYSTEM_RECOVERING",
        "COMPLETE",
    ]
    # Check that all expected states are present and in order
    filtered = [s for s in states if s in expected_order]
    assert filtered == expected_order, f"State order mismatch: {filtered}"


@pytest.mark.asyncio
async def test_stream_evidence_arrived_fires_six_times(test_client):
    """EVIDENCE_ARRIVED fires exactly six times (one per investigator)."""
    _, events = await _ingest_and_stream(test_client)
    evidence_events = [e for e in events if e["type"] == "EVIDENCE_ARRIVED"]
    assert len(evidence_events) == 6, (
        f"Expected 6 EVIDENCE_ARRIVED events, got {len(evidence_events)}"
    )


@pytest.mark.asyncio
async def test_stream_evidence_arrived_has_agent_id(test_client):
    """Each EVIDENCE_ARRIVED event carries a non-empty agent_id."""
    _, events = await _ingest_and_stream(test_client)
    for ev in (e for e in events if e["type"] == "EVIDENCE_ARRIVED"):
        assert ev.get("agent_id"), f"EVIDENCE_ARRIVED missing agent_id: {ev}"


@pytest.mark.asyncio
async def test_stream_causal_chain_has_root_cause(test_client):
    """CAUSAL_CHAIN event carries a chain with a root_cause_node_id."""
    _, events = await _ingest_and_stream(test_client)
    chain_events = [e for e in events if e["type"] == "CAUSAL_CHAIN"]
    assert len(chain_events) == 1, "Expected exactly one CAUSAL_CHAIN event"
    chain = chain_events[0]["chain"]
    assert chain.get("root_cause_node_id"), "CAUSAL_CHAIN missing root_cause_node_id"


@pytest.mark.asyncio
async def test_stream_fix_proposed_has_positive_confidence(test_client):
    """FIX_PROPOSED event carries a fix with confidence > 0."""
    _, events = await _ingest_and_stream(test_client)
    fix_events = [e for e in events if e["type"] == "FIX_PROPOSED"]
    assert len(fix_events) == 1, "Expected exactly one FIX_PROPOSED event"
    fix = fix_events[0]["fix"]
    assert fix["confidence"] > 0, "FIX_PROPOSED confidence should be > 0"


@pytest.mark.asyncio
async def test_stream_validation_result_passed_for_scenario_001(test_client):
    """VALIDATION_RESULT carries PASSED status for scenario-001."""
    _, events = await _ingest_and_stream(test_client)
    val_events = [e for e in events if e["type"] == "VALIDATION_RESULT"]
    assert len(val_events) == 1, "Expected exactly one VALIDATION_RESULT event"
    result = val_events[0]["result"]
    assert result["status"] == "PASSED", f"Expected PASSED, got {result['status']}"


@pytest.mark.asyncio
async def test_stream_report_ready_has_report_id(test_client):
    """REPORT_READY event carries a non-empty report_id."""
    pipeline_id, events = await _ingest_and_stream(test_client)
    report_events = [e for e in events if e["type"] == "REPORT_READY"]
    assert len(report_events) == 1, "Expected exactly one REPORT_READY event"
    assert report_events[0]["report_id"].startswith("report-"), (
        f"Unexpected report_id: {report_events[0]['report_id']}"
    )


@pytest.mark.asyncio
async def test_stream_complete_is_last_state_transition(test_client):
    """COMPLETE is the final STATE_TRANSITION in the stream."""
    _, events = await _ingest_and_stream(test_client)
    state_events = [e for e in events if e["type"] == "STATE_TRANSITION"]
    assert state_events, "No STATE_TRANSITION events found"
    assert state_events[-1]["state"] == "COMPLETE", (
        f"Last state should be COMPLETE, got {state_events[-1]['state']}"
    )


@pytest.mark.asyncio
async def test_stream_events_have_ts_field(test_client):
    """Every SSE event carries a 'ts' timestamp field."""
    _, events = await _ingest_and_stream(test_client)
    for ev in events:
        assert "ts" in ev, f"Event missing 'ts' field: {ev}"


@pytest.mark.asyncio
async def test_stream_ordering_evidence_before_causal_chain(test_client):
    """All EVIDENCE_ARRIVED events appear before the CAUSAL_CHAIN event."""
    _, events = await _ingest_and_stream(test_client)
    types = [e["type"] for e in events]
    last_evidence_idx = max(
        (i for i, t in enumerate(types) if t == "EVIDENCE_ARRIVED"),
        default=-1,
    )
    chain_idx = next((i for i, t in enumerate(types) if t == "CAUSAL_CHAIN"), -1)
    assert last_evidence_idx < chain_idx, (
        "All EVIDENCE_ARRIVED events must precede CAUSAL_CHAIN"
    )


@pytest.mark.asyncio
async def test_stream_ordering_fix_after_chain(test_client):
    """FIX_PROPOSED appears after CAUSAL_CHAIN."""
    _, events = await _ingest_and_stream(test_client)
    types = [e["type"] for e in events]
    chain_idx = next((i for i, t in enumerate(types) if t == "CAUSAL_CHAIN"), -1)
    fix_idx = next((i for i, t in enumerate(types) if t == "FIX_PROPOSED"), -1)
    assert chain_idx < fix_idx, "FIX_PROPOSED must appear after CAUSAL_CHAIN"


@pytest.mark.asyncio
async def test_report_endpoint_returns_full_report_after_stream(test_client):
    """GET /api/report/{id} returns the full RecoveryReport after stream completes."""
    pipeline_id, _ = await _ingest_and_stream(test_client)

    report_resp = await test_client.get(f"/api/report/{pipeline_id}")
    assert report_resp.status_code == 200, report_resp.text
    data = report_resp.json()["data"]

    assert data["pipeline_id"] == pipeline_id
    assert data["report_id"] == f"report-{pipeline_id}"
    assert data["proposed_fix"]["confidence"] > 0
    assert data["validation_result"]["status"] == "PASSED"
    assert "root_cause_node_id" in data["causal_chain"]
    assert data["root_cause_summary"]
    assert data["causal_explanation"]


@pytest.mark.asyncio
async def test_report_includes_counterfactual(test_client):
    """RecoveryReport includes counterfactual with before/after state."""
    pipeline_id, _ = await _ingest_and_stream(test_client)
    report_resp = await test_client.get(f"/api/report/{pipeline_id}")
    assert report_resp.status_code == 200
    cf = report_resp.json()["data"]["counterfactual"]

    assert "before_state" in cf
    assert "after_state" in cf
    assert "changed_nodes" in cf
    assert len(cf["changed_nodes"]) > 0, "At least one node should change in counterfactual"
    assert cf["narrative"]


@pytest.mark.asyncio
async def test_report_evidence_summary_has_six_entries(test_client):
    """RecoveryReport evidence_summary has one entry per investigator."""
    pipeline_id, _ = await _ingest_and_stream(test_client)
    report_resp = await test_client.get(f"/api/report/{pipeline_id}")
    evidence_summary = report_resp.json()["data"]["evidence_summary"]
    assert len(evidence_summary) == 6, (
        f"Expected 6 evidence entries, got {len(evidence_summary)}"
    )


@pytest.mark.asyncio
async def test_stream_404_for_unknown_pipeline(test_client):
    """GET /api/stream/{id} returns 404 for a pipeline that does not exist."""
    resp = await test_client.get("/api/stream/does-not-exist-xyz")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_report_404_for_unknown_pipeline(test_client):
    """GET /api/report/{id} returns 404 for a pipeline that does not exist."""
    resp = await test_client.get("/api/report/does-not-exist-xyz")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_report_202_when_stream_not_yet_run(test_client):
    """GET /api/report/{id} returns 202 when pipeline exists but stream not run yet."""
    resp = await test_client.post("/api/ingest", json=_SCENARIO_EVENT)
    pipeline_id = resp.json()["data"]["pipeline_id"]

    # Do NOT run the stream — report should not exist yet
    report_resp = await test_client.get(f"/api/report/{pipeline_id}")
    assert report_resp.status_code == 202
