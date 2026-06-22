import asyncio
from unittest.mock import MagicMock

import pytest

from src.web.events import EventBus, CrewCallbackAdapter


@pytest.mark.asyncio
async def test_event_bus_publishes_to_subscribers():
    bus = EventBus()
    received = []

    async def sub():
        async for event in bus.subscribe():
            received.append(event)
            if len(received) >= 2:
                break

    task = asyncio.create_task(sub())
    await asyncio.sleep(0.01)
    bus.publish({"type": "a"})
    bus.publish({"type": "b"})
    await asyncio.wait_for(task, timeout=1.0)
    assert [e["type"] for e in received] == ["a", "b"]


def test_event_bus_publish_with_no_subscribers():
    bus = EventBus()
    bus.publish({"type": "x"})  # should not crash


@pytest.mark.asyncio
async def test_event_bus_replays_terminal_event_to_late_subscriber():
    bus = EventBus()
    terminal = {"type": "run.complete", "run_id": "run-1"}
    bus.publish(terminal)

    subscription = bus.subscribe()
    received = await anext(subscription)
    await subscription.aclose()

    assert received == terminal


@pytest.mark.asyncio
async def test_event_bus_multiple_subscribers():
    bus = EventBus()
    a, b = [], []

    async def sub_a():
        async for event in bus.subscribe():
            a.append(event)
            if len(a) >= 1:
                break

    async def sub_b():
        async for event in bus.subscribe():
            b.append(event)
            if len(b) >= 1:
                break

    t1 = asyncio.create_task(sub_a())
    t2 = asyncio.create_task(sub_b())
    await asyncio.sleep(0.01)
    bus.publish({"type": "shared"})
    await asyncio.wait_for(asyncio.gather(t1, t2), timeout=1.0)
    assert a == [{"type": "shared"}]
    assert b == [{"type": "shared"}]


def test_crew_callback_adapter_emits_agent_start():
    bus = EventBus()
    bus.publish = MagicMock(wraps=bus.publish)
    adapter = CrewCallbackAdapter(bus)

    adapter.on_agent_start(agent_name="market_analyst", round_name="round1")
    args, _ = bus.publish.call_args
    assert args[0]["type"] == "agent.start"
    assert args[0]["agent"] == "market_analyst"


def test_crew_callback_adapter_emits_tool_end():
    bus = EventBus()
    bus.publish = MagicMock(wraps=bus.publish)
    adapter = CrewCallbackAdapter(bus)

    adapter.on_tool_end(
        agent_name="market_analyst", tool_name="search",
        input_preview="AI Agent", output_preview="...",
        evidence_id="ev-1",
    )
    args, _ = bus.publish.call_args
    assert args[0]["type"] == "tool.end"
    assert args[0]["evidence_id"] == "ev-1"


def test_crew_callback_adapter_emits_challenge_events():
    bus = EventBus()
    bus.publish = MagicMock(wraps=bus.publish)
    adapter = CrewCallbackAdapter(bus)

    adapter.on_challenge_issued(
        challenge_id="ch-1", issuer="market_analyst",
        target="finance_analyst", claim="LTV",
        reason="benchmark says X",
    )
    adapter.on_challenge_responded(
        challenge_id="ch-1", target="finance_analyst",
        response="adjusted", verdict="modified",
    )

    assert bus.publish.call_count == 2
    first_call = bus.publish.call_args_list[0][0][0]
    assert first_call["type"] == "challenge.issued"
    second_call = bus.publish.call_args_list[1][0][0]
    assert second_call["type"] == "challenge.responded"
