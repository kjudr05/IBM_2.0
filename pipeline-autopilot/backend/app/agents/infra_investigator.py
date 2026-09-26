"""
InfraInvestigator — analyses Dockerfile, CI configuration, and environment.

Prompt key : ``"infra_investigator"``
Evidence   : :class:`~app.models.evidence.InfraEvidence`
Input used : ``event.dockerfile_content``, ``event.ci_config_content``
"""

from __future__ import annotations

import uuid

from pydantic import ValidationError

from app.agents.base import BaseInvestigator
from app.models.events import PipelineFailureEvent
from app.models.evidence import EvidenceSource, InfraEvidence


class InfraInvestigator(BaseInvestigator):
    """
    Investigates infrastructure configuration to detect environment-level causes.

    Calls the provider with ``"infra_investigator"`` and validates the
    response against :class:`InfraEvidence`.
    """

    PROMPT_KEY = "infra_investigator"
    agent_id = "infra_investigator"

    async def investigate(self, event: PipelineFailureEvent) -> InfraEvidence:
        """
        Query the provider for infrastructure analysis and return :class:`InfraEvidence`.

        Raises
        ------
        ValueError
            Propagated from the provider or raised on schema validation failure.
        """
        raw = await self._provider.query(self._scenario_id, self.PROMPT_KEY)

        source = EvidenceSource(
            agent_id=self.agent_id,
            input_file="dockerfile.txt,ci_config.yml",
            extraction_method="mock",
        )

        raw.update(
            {
                "evidence_id": f"ev-infra-{uuid.uuid4().hex[:8]}",
                "pipeline_id": event.pipeline_run_id,
                "source": source,
            }
        )

        try:
            return InfraEvidence(**raw)
        except ValidationError as exc:
            raise ValueError(
                f"InfraInvestigator: provider response failed InfraEvidence validation: {exc}"
            ) from exc
