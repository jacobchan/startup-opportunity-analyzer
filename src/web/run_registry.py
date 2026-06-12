from src.web.events import EventBus


class RunRegistry:
    """Maps run_id -> EventBus for SSE stream lookup in a single process."""

    def __init__(self):
        self._buses: dict[str, EventBus] = {}

    def create(self, run_id: str) -> EventBus:
        bus = EventBus()
        self._buses[run_id] = bus
        return bus

    def get(self, run_id: str) -> EventBus | None:
        return self._buses.get(run_id)


registry = RunRegistry()
