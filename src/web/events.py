import asyncio
from typing import AsyncIterator


class EventBus:
    """In-process event bus. Multiple subscribers iterate asynchronously."""

    def __init__(self):
        self._subscribers: list[asyncio.Queue] = []
        self._terminal_event: dict | None = None

    def publish(self, event: dict) -> None:
        if event.get("type") in ("run.complete", "run.failed"):
            self._terminal_event = event
        for q in self._subscribers:
            q.put_nowait(event)

    async def subscribe(self) -> AsyncIterator[dict]:
        q: asyncio.Queue = asyncio.Queue()
        self._subscribers.append(q)
        if self._terminal_event is not None:
            q.put_nowait(self._terminal_event)
        try:
            while True:
                event = await q.get()
                yield event
        finally:
            self._subscribers.remove(q)


class CrewCallbackAdapter:
    """Adapts CrewAI step_callback events into EventBus events."""

    def __init__(self, bus: EventBus):
        self._bus = bus

    def on_agent_start(self, agent_name: str, round_name: str) -> None:
        self._bus.publish({
            "type": "agent.start",
            "agent": agent_name,
            "round": round_name,
        })

    def on_agent_end(self, agent_name: str, round_name: str, output_json_summary: dict | None = None) -> None:
        self._bus.publish({
            "type": "agent.end",
            "agent": agent_name,
            "round": round_name,
            "output_summary": output_json_summary or {},
        })

    def on_tool_start(self, agent_name: str, tool_name: str, input_preview: str) -> None:
        self._bus.publish({
            "type": "tool.start",
            "agent": agent_name,
            "tool": tool_name,
            "input_preview": input_preview[:200],
        })

    def on_tool_end(
        self, agent_name: str, tool_name: str,
        input_preview: str, output_preview: str, evidence_id: str | None = None,
    ) -> None:
        self._bus.publish({
            "type": "tool.end",
            "agent": agent_name,
            "tool": tool_name,
            "evidence_id": evidence_id,
            "output_preview": output_preview[:200],
        })

    def on_challenge_issued(self, challenge_id: str, issuer: str, target: str, claim: str, reason: str) -> None:
        self._bus.publish({
            "type": "challenge.issued",
            "challenge_id": challenge_id,
            "issuer": issuer,
            "target": target,
            "claim": claim,
            "reason": reason,
        })

    def on_challenge_responded(self, challenge_id: str, target: str, response: str, verdict: str) -> None:
        self._bus.publish({
            "type": "challenge.responded",
            "challenge_id": challenge_id,
            "target": target,
            "response": response,
            "verdict": verdict,
        })
