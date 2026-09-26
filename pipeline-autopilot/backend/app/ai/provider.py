# Abstract AIProvider interface — all LLM/AI backends implement this
# Investigators call provider.query(scenario_id, prompt_key) and receive a
# plain dict that they can validate against their evidence schema.
#
# Design notes:
#   - `query` is async so real providers (watsonx, OpenAI) can await HTTP calls
#     without any change to the interface or the investigator classes.
#   - We deliberately avoid `analyze(prompt: str)` and `extract_structured()`
#     from an earlier sketch because arbitrary natural-language prompts make
#     deterministic testing impossible.  Keyed dispatch is simpler and safer
#     for the MVP and still lets a real provider ignore the key and use the
#     prompt_key as a system-prompt selector.

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class AIProvider(ABC):
    """
    Abstract base for all AI / LLM provider implementations.

    Each investigator calls::

        raw: dict = await provider.query(scenario_id, prompt_key)

    and then validates ``raw`` against its own Pydantic evidence schema.

    Parameters
    ----------
    scenario_id:
        Identifies the pipeline-failure scenario being investigated
        (e.g. ``"scenario-001"``).
    prompt_key:
        Identifies which investigator is asking and what evidence it expects
        (e.g. ``"log_investigator"``, ``"dependency_investigator"``).

    Returns
    -------
    dict[str, Any]
        A plain dict whose structure matches the evidence schema for the
        given prompt_key.  The caller is responsible for validation.

    Raises
    ------
    ValueError
        If ``scenario_id`` or ``prompt_key`` is not supported by this
        provider implementation.
    """

    @abstractmethod
    async def query(self, scenario_id: str, prompt_key: str) -> dict[str, Any]:
        """Return deterministic or LLM-generated evidence data."""
        ...
