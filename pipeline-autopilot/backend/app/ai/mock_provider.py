"""
MockProvider — deterministic AI provider for scenario-001.

Returns pre-written, schema-valid evidence dicts keyed on
(scenario_id, prompt_key).  No external API calls are made; the module
works fully offline.

Supported scenarios
-------------------
    "scenario-001"  — "The Silent Semver Break"

Supported prompt keys  (one per investigator)
---------------------------------------------
    "log_investigator"          →  FailureEvidence  fields
    "code_investigator"         →  ChangeEvidence   fields
    "dependency_investigator"   →  DependencyEvidence fields
    "test_investigator"         →  TestRunEvidence  fields
    "infra_investigator"        →  InfraEvidence    fields
    "history_investigator"      →  HistoricalEvidence fields

Each dict contains all required evidence fields EXCEPT the identity
fields that only the investigator can supply at call-time
(evidence_id, pipeline_id, source, created_at).  The investigator is
responsible for merging those in before constructing its Pydantic model.

Source-of-truth for all values
-------------------------------
All literal strings/numbers are taken verbatim from:
    sample-data/scenario-001/ci_log.txt
    sample-data/scenario-001/git_diff.patch
    sample-data/scenario-001/dependency_before.json
    sample-data/scenario-001/dependency_after.json
    sample-data/scenario-001/test_results.xml
    sample-data/scenario-001/dockerfile.txt
    sample-data/scenario-001/ci_config.yml
    sample-data/scenario-001/history.json
    sample-data/scenario-001/failure_event.json
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from app.ai.provider import AIProvider

# ---------------------------------------------------------------------------
# Scenario registry
# ---------------------------------------------------------------------------

_SUPPORTED_SCENARIOS: frozenset[str] = frozenset({"scenario-001"})

# ---------------------------------------------------------------------------
# Evidence data — keyed by prompt_key
#
# Every dict is a *template*: the provider returns a deep-copy so callers
# can freely mutate the result without corrupting shared state.
#
# Fields that belong to BaseEvidence but are caller-supplied at run-time
# (evidence_id, pipeline_id, source, created_at) are NOT included here.
# ---------------------------------------------------------------------------

_SCENARIO_001: dict[str, dict[str, Any]] = {
    # ------------------------------------------------------------------
    # log_investigator → FailureEvidence
    # ------------------------------------------------------------------
    "log_investigator": {
        "evidence_type": "failure",
        "summary": (
            "TypeError: formatCurrency is not a function — "
            "3 payment-related tests failed in the 'test' stage"
        ),
        "confidence": 0.98,
        "error_class": "TypeError",
        "error_message": "formatCurrency is not a function",
        "stack_trace": [
            "TypeError: formatCurrency is not a function",
            "    at Object.formatCurrency (src/payments/invoice.js:12:5)",
            "    at Object.<anonymous> (src/payments/invoice.test.js:23:18)",
        ],
        "affected_stage": "test",
        "failure_timestamp": "2024-03-15T14:32:16Z",
        "severity": "critical",
        "log_excerpt": (
            "[14:32:16] FAIL src/payments/invoice.test.js\n"
            "[14:32:16]   ● PaymentsService::test_format_invoice\n"
            "\n"
            "    TypeError: formatCurrency is not a function\n"
            "\n"
            "      at Object.formatCurrency (src/payments/invoice.js:12:5)\n"
            "      at Object.<anonymous> (src/payments/invoice.test.js:23:18)\n"
            "[14:32:16] Tests: 3 failed, 14 passed, 17 total\n"
            "[14:32:16] BUILD FAILED"
        ),
        "file_path": "src/payments/invoice.js",
        "line_number": 12,
    },

    # ------------------------------------------------------------------
    # code_investigator → ChangeEvidence
    # ------------------------------------------------------------------
    "code_investigator": {
        "evidence_type": "change",
        "summary": (
            "package.json bumped utility-lib from ^2.3.1 to ^3.0.0 "
            "in commit a1b2c3d4 on branch feature/update-deps"
        ),
        "confidence": 0.97,
        "commit_sha": "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2",
        "author": "dev@acme.com",
        "commit_message": "chore: bump utility-lib to 3.0.0",
        "commit_timestamp": "2024-03-15T14:00:00Z",
        "changed_files": [
            {
                "path": "package.json",
                "additions": 1,
                "deletions": 1,
                "diff_hunk": (
                    "@@ -5,7 +5,7 @@\n"
                    '   "dependencies": {\n'
                    '     "express": "^4.18.2",\n'
                    '-    "utility-lib": "^2.3.1",\n'
                    '+    "utility-lib": "^3.0.0",\n'
                    '     "lodash": "^4.17.21"\n'
                    "   }\n"
                    " }"
                ),
            }
        ],
        "changed_functions": [],
        "total_additions": 1,
        "total_deletions": 1,
    },

    # ------------------------------------------------------------------
    # dependency_investigator → DependencyEvidence
    # ------------------------------------------------------------------
    "dependency_investigator": {
        "evidence_type": "dependency",
        "summary": (
            "utility-lib upgraded from 2.3.1 → 3.0.0 (major version bump); "
            "formatCurrency() was removed in v3 — breaking change for payments-service"
        ),
        "confidence": 0.99,
        "added": [],
        "removed": [],
        "changed": [
            {
                "name": "utility-lib",
                "old_version": "2.3.1",
                "new_version": "3.0.0",
                "affected_component": "acme/payments-service",
            }
        ],
        "breaking_changes": [
            "utility-lib 3.0.0 removes formatCurrency() which was exported in 2.x; "
            "payments-service calls this function in invoice.js, totals.js, and receipt.js"
        ],
    },

    # ------------------------------------------------------------------
    # test_investigator → TestRunEvidence
    # ------------------------------------------------------------------
    "test_investigator": {
        "evidence_type": "test",
        "summary": (
            "3 of 17 payment tests failed — all trace to "
            "formatCurrency is not a function (TypeError)"
        ),
        "confidence": 0.99,
        "failed_tests": [
            {
                "name": "test_format_invoice",
                "class_name": "PaymentsService",
                "failure_message": "TypeError: formatCurrency is not a function",
                "duration_ms": 12.0,
            },
            {
                "name": "test_calculate_total",
                "class_name": "PaymentsService",
                "failure_message": "TypeError: formatCurrency is not a function",
                "duration_ms": 9.0,
            },
            {
                "name": "test_generate_receipt",
                "class_name": "PaymentsService",
                "failure_message": "TypeError: formatCurrency is not a function",
                "duration_ms": 11.0,
            },
        ],
        "flaky_tests": [],
        "regression_tests": [
            "test_format_invoice",
            "test_calculate_total",
            "test_generate_receipt",
        ],
        "total_run": 17,
        "total_failed": 3,
        "total_passed": 14,
        "total_skipped": 0,
    },

    # ------------------------------------------------------------------
    # infra_investigator → InfraEvidence
    # ------------------------------------------------------------------
    "infra_investigator": {
        "evidence_type": "infra",
        "summary": (
            "Dockerfile and CI config are healthy; "
            "node:20-alpine base image matches CI node-version: '20'; "
            "no infrastructure cause detected"
        ),
        "confidence": 0.93,
        "dockerfile_issues": [],
        "ci_config_issues": [],
        "env_var_issues": [],
        "image_changes": [],
        "config_source": ".github/workflows/ci.yml",
    },

    # ------------------------------------------------------------------
    # history_investigator → HistoricalEvidence
    # ------------------------------------------------------------------
    "history_investigator": {
        "evidence_type": "historical",
        "summary": (
            "1 similar prior failure found (run-20240108-007): "
            "utility-lib 2.2.0 also introduced a breaking change; "
            "fix was to pin to last known-good version"
        ),
        "confidence": 0.91,
        "similar_failures": [
            {
                "run_id": "run-20240108-007",
                "date": "2024-01-08T09:14:00Z",
                "root_cause": "utility-lib 2.2.0 introduced breaking change in parseAmount()",
                "fix_applied": "Pinned utility-lib to 2.1.5",
                "similarity_score": 0.92,
            }
        ],
        "recurrence_count": 1,
        "last_seen": "2024-01-08T09:14:00Z",
        "known_fix": "Pin utility-lib back to the last compatible version (2.3.1)",
    },
}

# ---------------------------------------------------------------------------
# Supported prompt keys
# ---------------------------------------------------------------------------

SUPPORTED_PROMPT_KEYS: frozenset[str] = frozenset(_SCENARIO_001.keys())


# ---------------------------------------------------------------------------
# MockProvider
# ---------------------------------------------------------------------------


class MockProvider(AIProvider):
    """
    Deterministic, offline AI provider for scenario-001.

    Instantiation
    -------------
    No constructor arguments required.  The provider carries no mutable
    state — it is safe to share a single instance across all investigators.

    Usage
    -----
    ::

        provider = MockProvider()
        raw = await provider.query("scenario-001", "log_investigator")
        # raw is a plain dict ready to be merged with identity fields
        # and validated against FailureEvidence

    Error behaviour
    ---------------
    * Unknown scenario_id → ``ValueError`` with a descriptive message.
    * Unknown prompt_key  → ``ValueError`` with a descriptive message.
    No fallback / silent return — callers must handle the error explicitly.
    """

    # ------------------------------------------------------------------
    # AIProvider implementation
    # ------------------------------------------------------------------

    async def query(self, scenario_id: str, prompt_key: str) -> dict[str, Any]:
        """
        Return a deep-copy of the deterministic evidence dict for the given
        scenario and prompt key.

        Parameters
        ----------
        scenario_id:
            Must be ``"scenario-001"`` for this provider.
        prompt_key:
            One of the six investigator keys (see module docstring).

        Raises
        ------
        ValueError
            If ``scenario_id`` or ``prompt_key`` is not supported.
        """
        if scenario_id not in _SUPPORTED_SCENARIOS:
            supported = ", ".join(sorted(_SUPPORTED_SCENARIOS))
            raise ValueError(
                f"MockProvider does not support scenario '{scenario_id}'. "
                f"Supported scenarios: {supported}"
            )

        scenario_data = _SCENARIO_001  # only one scenario for now
        if prompt_key not in scenario_data:
            supported = ", ".join(sorted(scenario_data.keys()))
            raise ValueError(
                f"MockProvider does not support prompt key '{prompt_key}' "
                f"for scenario '{scenario_id}'. "
                f"Supported keys: {supported}"
            )

        return deepcopy(scenario_data[prompt_key])
