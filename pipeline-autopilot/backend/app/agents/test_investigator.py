"""
TestInvestigator — analyses test-run results and regression information.

Prompt key : ``"test_investigator"``
Evidence   : :class:`~app.models.evidence.TestRunEvidence`
Input used : ``event.test_results_xml``
"""

from __future__ import annotations

import uuid

from pydantic import ValidationError

from app.agents.base import BaseInvestigator
from app.models.events import PipelineFailureEvent
from app.models.evidence import EvidenceSource, TestRunEvidence


class TestInvestigator(BaseInvestigator):
    """
    Investigates test results to identify failures and regressions.

    Calls the provider with ``"test_investigator"`` and validates the
    response against :class:`TestRunEvidence`.
    """

    PROMPT_KEY = "test_investigator"
    agent_id = "test_investigator"

    async def investigate(self, event: PipelineFailureEvent) -> TestRunEvidence:
        """
        Query the provider for test-result analysis and return :class:`TestRunEvidence`.

        Raises
        ------
        ValueError
            Propagated from the provider or raised on schema validation failure.
        """
        raw = await self._provider.query(self._scenario_id, self.PROMPT_KEY)

        source = EvidenceSource(
            agent_id=self.agent_id,
            input_file="test_results.xml",
            extraction_method="mock",
        )

        raw.update(
            {
                "evidence_id": f"ev-test-{uuid.uuid4().hex[:8]}",
                "pipeline_id": event.pipeline_run_id,
                "source": source,
            }
        )

        try:
            return TestRunEvidence(**raw)
        except ValidationError as exc:
            raise ValueError(
                f"TestInvestigator: provider response failed TestRunEvidence validation: {exc}"
            ) from exc
