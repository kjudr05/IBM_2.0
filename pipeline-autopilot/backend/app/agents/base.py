"""
BaseInvestigator — abstract interface all six investigation agents implement.

Every investigator:
  - holds an AIProvider instance (injected at construction)
  - holds a scenario_id that identifies which scenario is being investigated
  - exposes a single async `investigate(event) -> BaseEvidence` method
  - is stateless: calling investigate() twice with the same inputs is idempotent

The orchestrator (Task 6) will construct each investigator with the provider
and scenario_id, then call investigate() concurrently via asyncio.gather.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.ai.provider import AIProvider
from app.models.events import PipelineFailureEvent
from app.models.evidence import BaseEvidence


class BaseInvestigator(ABC):
    """
    Abstract base for all six investigators.

    Parameters
    ----------
    provider:
        The AI provider to query.  Investigators call
        ``await self._provider.query(self._scenario_id, self.PROMPT_KEY)``
        and validate the returned dict against their evidence schema.
    scenario_id:
        The scenario being investigated (e.g. ``"scenario-001"``).
        Passed through to every provider query unchanged.

    Class attributes
    ----------------
    PROMPT_KEY : str
        The prompt key this investigator sends to the provider.
        Each subclass must declare it at the class level.
    agent_id : str
        Stable identifier for this agent (used in EvidenceSource provenance).
        Each subclass must declare it at the class level.
    """

    # Subclasses must override these two class-level constants.
    PROMPT_KEY: str
    agent_id: str

    def __init__(self, provider: AIProvider, scenario_id: str) -> None:
        self._provider = provider
        self._scenario_id = scenario_id

    @abstractmethod
    async def investigate(self, event: PipelineFailureEvent) -> BaseEvidence:
        """
        Investigate a pipeline failure and return typed evidence.

        Parameters
        ----------
        event:
            The ingested pipeline failure event carrying all raw source data.

        Returns
        -------
        BaseEvidence
            A concrete evidence subclass populated from the provider response.

        Raises
        ------
        ValueError
            If the provider returns data that cannot be validated against
            the expected evidence schema, or if the provider itself raises.
        """
        ...
