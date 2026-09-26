"""
HistoryInvestigator — analyses prior CI failures for pattern matching.

Prompt key : ``"history_investigator"``
Evidence   : :class:`~app.models.evidence.HistoricalEvidence`
Input used : ``event.history``
"""

from __future__ import annotations

import uuid

from pydantic import ValidationError

from app.agents.base import BaseInvestigator
from app.models.events import PipelineFailureEvent
from app.models.evidence import EvidenceSource, HistoricalEvidence


class HistoryInvestigator(BaseInvestigator):
    """
    Investigates historical CI failures to identify recurrence patterns.

    Calls the provider with ``"history_investigator"`` and validates the
    response against :class:`HistoricalEvidence`.
    """

    PROMPT_KEY = "history_investigator"
    agent_id = "history_investigator"

    async def investigate(self, event: PipelineFailureEvent) -> HistoricalEvidence:
        """
        Query the provider for historical analysis and return :class:`HistoricalEvidence`.

        Raises
        ------
        ValueError
            Propagated from the provider or raised on schema validation failure.
        """
        raw = await self._provider.query(self._scenario_id, self.PROMPT_KEY)

        source = EvidenceSource(
            agent_id=self.agent_id,
            input_file="history.json",
            extraction_method="mock",
        )

        raw.update(
            {
                "evidence_id": f"ev-hist-{uuid.uuid4().hex[:8]}",
                "pipeline_id": event.pipeline_run_id,
                "source": source,
            }
        )

        try:
            return HistoricalEvidence(**raw)
        except ValidationError as exc:
            raise ValueError(
                f"HistoryInvestigator: provider response failed HistoricalEvidence validation: {exc}"
            ) from exc
