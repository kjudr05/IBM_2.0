"""
EvidenceBus — in-process async collector for evidence artifacts.

The bus provides the coordination point between the investigators (producers)
and the orchestrator (consumer).  For the MVP it is entirely in-process;
a message queue could replace it later without changing the investigator or
orchestrator interfaces.

Design
------
- ``publish(evidence)`` — store one artifact, thread-safe for async callers.
- ``collect()`` — return all artifacts published so far (insertion-ordered).
- ``clear()`` — reset the bus (useful in tests).

The bus is stateful but carries *no* domain logic.  It knows nothing about
scenarios, investigators, or what the evidence means.

Usage
-----
::

    bus = EvidenceBus()

    # inside each investigator result handler:
    await bus.publish(evidence_artifact)

    # after all investigators complete:
    all_evidence = bus.collect()
"""

from __future__ import annotations

import asyncio
from typing import Sequence

from app.models.evidence import BaseEvidence


class EvidenceBus:
    """
    Simple in-process evidence collector.

    All public methods are safe to call from multiple concurrent coroutines
    because the underlying list is protected by an ``asyncio.Lock``.

    Attributes are not exposed directly — use the public API only.
    """

    def __init__(self) -> None:
        self._artifacts: list[BaseEvidence] = []
        self._lock: asyncio.Lock = asyncio.Lock()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def publish(self, evidence: BaseEvidence) -> None:
        """
        Publish one evidence artifact to the bus.

        Parameters
        ----------
        evidence:
            A concrete :class:`~app.models.evidence.BaseEvidence` subclass
            instance produced by an investigator.

        Notes
        -----
        Publication order is the order in which coroutines acquire the lock,
        which for ``asyncio.gather`` is non-deterministic.  Consumers that
        require a specific ordering must sort by ``created_at`` themselves.
        """
        async with self._lock:
            self._artifacts.append(evidence)

    def collect(self) -> list[BaseEvidence]:
        """
        Return all evidence artifacts published to this bus.

        Returns a *copy* of the internal list so that subsequent publications
        do not mutate the returned collection.

        Returns
        -------
        list[BaseEvidence]
            All artifacts in publication order.  Empty list if nothing has
            been published yet.
        """
        return list(self._artifacts)

    def clear(self) -> None:
        """
        Remove all artifacts.  Primarily used in tests to reset state.

        Not async — safe to call outside a coroutine.
        """
        self._artifacts.clear()

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------

    def __len__(self) -> int:
        return len(self._artifacts)

    def __repr__(self) -> str:  # pragma: no cover
        return f"EvidenceBus(count={len(self._artifacts)})"
