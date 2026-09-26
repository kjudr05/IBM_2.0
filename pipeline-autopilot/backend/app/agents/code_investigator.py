"""
CodeInvestigator — analyses git diffs and commit metadata.

Prompt key : ``"code_investigator"``
Evidence   : :class:`~app.models.evidence.ChangeEvidence`
Input used : ``event.git_diff_patch``, ``event.commit_sha``
"""

from __future__ import annotations

import uuid

from pydantic import ValidationError

from app.agents.base import BaseInvestigator
from app.models.events import PipelineFailureEvent
from app.models.evidence import ChangeEvidence, EvidenceSource


class CodeInvestigator(BaseInvestigator):
    """
    Investigates the commit that triggered the pipeline to find what changed.

    Calls the provider with ``"code_investigator"`` and validates the
    response against :class:`ChangeEvidence`.
    """

    PROMPT_KEY = "code_investigator"
    agent_id = "code_investigator"

    async def investigate(self, event: PipelineFailureEvent) -> ChangeEvidence:
        """
        Query the provider for code-change analysis and return :class:`ChangeEvidence`.

        Raises
        ------
        ValueError
            Propagated from the provider or raised on schema validation failure.
        """
        raw = await self._provider.query(self._scenario_id, self.PROMPT_KEY)

        source = EvidenceSource(
            agent_id=self.agent_id,
            input_file="git_diff.patch",
            extraction_method="mock",
        )

        raw.update(
            {
                "evidence_id": f"ev-code-{uuid.uuid4().hex[:8]}",
                "pipeline_id": event.pipeline_run_id,
                "source": source,
            }
        )

        try:
            return ChangeEvidence(**raw)
        except ValidationError as exc:
            raise ValueError(
                f"CodeInvestigator: provider response failed ChangeEvidence validation: {exc}"
            ) from exc
