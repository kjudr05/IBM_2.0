"""
LogInvestigator — analyses CI logs, stack traces, and error timestamps.

Prompt key : ``"log_investigator"``
Evidence   : :class:`~app.models.evidence.FailureEvidence`
Input used : ``event.raw_log_text``, ``event.failure_stage``
"""

from __future__ import annotations

import uuid

from pydantic import ValidationError

from app.agents.base import BaseInvestigator
from app.models.events import PipelineFailureEvent
from app.models.evidence import EvidenceSource, FailureEvidence


class LogInvestigator(BaseInvestigator):
    """
    Investigates CI log output to identify the observable failure.

    Calls the provider with ``"log_investigator"`` and validates the
    response against :class:`FailureEvidence`.
    """

    PROMPT_KEY = "log_investigator"
    agent_id = "log_investigator"

    async def investigate(self, event: PipelineFailureEvent) -> FailureEvidence:
        """
        Query the provider for log analysis and return :class:`FailureEvidence`.

        Raises
        ------
        ValueError
            Propagated from the provider if the scenario or prompt key is
            unsupported, or raised here if the provider response fails
            Pydantic validation.
        """
        raw = await self._provider.query(self._scenario_id, self.PROMPT_KEY)

        source = EvidenceSource(
            agent_id=self.agent_id,
            input_file="ci_log.txt",
            extraction_method="mock",
        )

        raw.update(
            {
                "evidence_id": f"ev-log-{uuid.uuid4().hex[:8]}",
                "pipeline_id": event.pipeline_run_id,
                "source": source,
            }
        )

        try:
            return FailureEvidence(**raw)
        except ValidationError as exc:
            raise ValueError(
                f"LogInvestigator: provider response failed FailureEvidence validation: {exc}"
            ) from exc
