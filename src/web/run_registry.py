"""In-process mapping of run_id to SSE EventBus.

The bus is created in ``POST /runs`` and ``POST /runs/{id}/resume``,
and consumed by the corresponding ``GET /runs/{id}/stream`` handler.
To avoid an unbounded memory leak across long-lived processes, the
background task schedules bus cleanup after it has emitted a terminal event.
SSE consumers never release it: a disconnect commonly means the user
is refreshing and must be able to reconnect to the still-running bus. A
consumer that actually receives the terminal event may release it early.
"""

from __future__ import annotations

import logging

from src.web.events import EventBus

logger = logging.getLogger(__name__)


class RunRegistry:
    def __init__(self) -> None:
        self._buses: dict[str, EventBus] = {}

    def create(self, run_id: str) -> EventBus:
        """Create a fresh bus for a run. Overwrites any prior bus for
        the same id, which can happen when a run is resumed.
        """
        if run_id in self._buses:
            logger.warning("run registry: overwriting bus for %s", run_id)
        bus = EventBus()
        self._buses[run_id] = bus
        return bus

    def get(self, run_id: str) -> EventBus | None:
        return self._buses.get(run_id)

    def release(self, run_id: str) -> None:
        """Drop the bus for a finished run. Safe to call when the
        run was never registered.
        """
        self._buses.pop(run_id, None)

    def __len__(self) -> int:
        return len(self._buses)


registry = RunRegistry()
