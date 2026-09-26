"""
BobOrchestrator — coordinates all six investigators and collects their evidence.

Responsibilities (Task 6 scope)
--------------------------------
1. Receive a :class:`PipelineFailureEvent` and a ``scenario_id``.
2. Instantiate all six investigators with the given AI provider.
3. Dispatch all six investigations concurrently via ``asyncio.gather``.
4. Publish each successful evidence artifact to the :class:`EvidenceBus`.
5. Record per-investigator outcomes (success or exception).
6. Produce a :class:`InvestigationResult` carrying all collected evidence.

What the orchestrator does NOT do (kept for later tasks)
---------------------------------------------------------
- Causal chain construction (Task 7)
- Fix generation (Task 8)
- Counterfactual simulation (Task 8)
- SSE emission (Task 9)

The orchestrator answers *"What evidence did our investigators collect?"*.
It does NOT yet answer *"Why did the system fail?"*.

Error handling
--------------
- If one investigator raises, the exception is caught, recorded in
  ``InvestigationResult.errors``, and the other investigators' results are
  still collected.
- ``status`` is derived from the outcome set:
  - COMPLETE  — all 6 investigators succeeded
  - PARTIAL   — at least 1 succeeded, at least 1 failed
  - FAILED    — all 6 investigators failed
- Provider errors (e.g. unsupported scenario) propagate through as-is from
  each investigator; the orchestrator treats them the same as any other exception.

Usage
-----
::

    from app.ai.mock_provider import MockProvider
    from app.agents.orchestrator import BobOrchestrator

    orchestrator = BobOrchestrator(provider=MockProvider())
    result = await orchestrator.run(event, scenario_id="scenario-001")
    print(result.status)          # InvestigationStatus.COMPLETE
    print(len(result.evidence))   # 6
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import TYPE_CHECKING

from app.agents.code_investigator import CodeInvestigator
from app.agents.dependency_investigator import DependencyInvestigator
from app.agents.history_investigator import HistoryInvestigator
from app.agents.infra_investigator import InfraInvestigator
from app.agents.log_investigator import LogInvestigator
from app.agents.test_investigator import TestInvestigator
from app.ai.provider import AIProvider
from app.bus.evidence_bus import EvidenceBus
from app.models.events import PipelineFailureEvent
from app.models.evidence import BaseEvidence
from app.models.investigation import (
    InvestigationResult,
    InvestigationStatus,
    InvestigatorOutcome,
)

# The six investigator classes, in declaration order.
# Order does not affect concurrency — all run in parallel.
_INVESTIGATOR_CLASSES = [
    LogInvestigator,
    CodeInvestigator,
    DependencyInvestigator,
    TestInvestigator,
    InfraInvestigator,
    HistoryInvestigator,
]


class BobOrchestrator:
    """
    Coordinates the six investigators, collects evidence, returns a result.

    Parameters
    ----------
    provider:
        The AI provider injected into each investigator.
        Use :class:`~app.ai.mock_provider.MockProvider` for the MVP.

    Notes
    -----
    The orchestrator is stateless between calls.  A single instance can be
    reused to process multiple pipeline failures.  Each ``run()`` call creates
    a fresh :class:`EvidenceBus` so there is no cross-call contamination.
    """

    def __init__(self, provider: AIProvider) -> None:
        self._provider = provider

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def run(
        self,
        event: PipelineFailureEvent,
        scenario_id: str,
    ) -> InvestigationResult:
        """
        Run all six investigators concurrently and return the collected evidence.

        Parameters
        ----------
        event:
            The ingested pipeline failure event.
        scenario_id:
            The scenario identifier forwarded to every investigator and to the
            AI provider (e.g. ``"scenario-001"``).

        Returns
        -------
        InvestigationResult
            Contains all collected evidence artifacts, per-investigator outcomes,
            overall status, and timing information.

        Notes
        -----
        Exceptions from individual investigators are *caught* and recorded in
        :attr:`InvestigationResult.errors`.  They are never silently discarded —
        they appear in ``errors`` and in the corresponding
        :class:`InvestigatorOutcome`.
        """
        started_at = datetime.utcnow()
        bus = EvidenceBus()

        # Build investigator instances — all share the same provider and scenario.
        investigators = [
            cls(provider=self._provider, scenario_id=scenario_id)
            for cls in _INVESTIGATOR_CLASSES
        ]

        # Dispatch all investigators concurrently.
        # return_exceptions=True means asyncio.gather never raises; exceptions
        # are returned as result values so we can record them per-investigator.
        raw_results: list[BaseEvidence | BaseException] = await asyncio.gather(
            *[inv.investigate(event) for inv in investigators],
            return_exceptions=True,
        )

        # Process each result — publish successes, record failures.
        outcomes: list[InvestigatorOutcome] = []
        errors: dict[str, str] = {}

        for investigator, result in zip(investigators, raw_results):
            agent_id = investigator.agent_id

            if isinstance(result, BaseException):
                errors[agent_id] = str(result)
                outcomes.append(
                    InvestigatorOutcome(
                        agent_id=agent_id,
                        success=False,
                        evidence_id=None,
                        error=str(result),
                    )
                )
            else:
                await bus.publish(result)
                outcomes.append(
                    InvestigatorOutcome(
                        agent_id=agent_id,
                        success=True,
                        evidence_id=result.evidence_id,
                        error=None,
                    )
                )

        all_evidence = bus.collect()
        completed_at = datetime.utcnow()

        # Derive overall status.
        n_success = sum(1 for o in outcomes if o.success)
        n_total = len(outcomes)

        if n_success == n_total:
            status = InvestigationStatus.COMPLETE
        elif n_success > 0:
            status = InvestigationStatus.PARTIAL
        else:
            status = InvestigationStatus.FAILED

        return InvestigationResult(
            pipeline_id=event.pipeline_run_id,
            scenario_id=scenario_id,
            status=status,
            evidence=all_evidence,
            outcomes=outcomes,
            errors=errors,
            started_at=started_at,
            completed_at=completed_at,
        )
