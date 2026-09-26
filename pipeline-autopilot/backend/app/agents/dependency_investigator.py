"""
DependencyInvestigator — analyses before/after dependency manifests.

Prompt key : ``"dependency_investigator"``
Evidence   : :class:`~app.models.evidence.DependencyEvidence`
Input used : ``event.dependency_before``, ``event.dependency_after``
"""

from __future__ import annotations

import uuid

from pydantic import ValidationError

from app.agents.base import BaseInvestigator
from app.models.events import PipelineFailureEvent
from app.models.evidence import DependencyEvidence, EvidenceSource


class DependencyInvestigator(BaseInvestigator):
    """
    Investigates dependency changes between the before and after manifests.

    Calls the provider with ``"dependency_investigator"`` and validates the
    response against :class:`DependencyEvidence`.
    """

    PROMPT_KEY = "dependency_investigator"
    agent_id = "dependency_investigator"

    async def investigate(self, event: PipelineFailureEvent) -> DependencyEvidence:
        """
        Query the provider for dependency analysis and return :class:`DependencyEvidence`.

        Raises
        ------
        ValueError
            Propagated from the provider or raised on schema validation failure.
        """
        raw = await self._provider.query(self._scenario_id, self.PROMPT_KEY)

        source = EvidenceSource(
            agent_id=self.agent_id,
            input_file="dependency_before.json,dependency_after.json",
            extraction_method="mock",
        )

        raw.update(
            {
                "evidence_id": f"ev-dep-{uuid.uuid4().hex[:8]}",
                "pipeline_id": event.pipeline_run_id,
                "source": source,
            }
        )

        try:
            return DependencyEvidence(**raw)
        except ValidationError as exc:
            raise ValueError(
                f"DependencyInvestigator: provider response failed "
                f"DependencyEvidence validation: {exc}"
            ) from exc
