import asyncio
import json

import httpx
import pytest

from src.web.app import create_app
from src.web.run_registry import registry as _registry


@pytest.fixture
def app_with_patched_runner(monkeypatch):
    """Create FastAPI app with a no-op background runner."""
    monkeypatch.setattr("src.web.routes.runs._run_in_background", lambda *a: None)
    return create_app()


@pytest.mark.asyncio
async def test_stream_yields_published_message(app_with_patched_runner):
    transport = httpx.ASGITransport(app=app_with_patched_runner)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # Create a run
        resp = await client.post("/runs", json={"startup_idea": "x"})
        run_id = resp.json()["run_id"]
        bus = _registry.get(run_id)

        # Run the stream reader in a background task so we can publish concurrently.
        found_event = []

        async def read_stream():
            async with client.stream("GET", f"/runs/{run_id}/stream") as response:
                async for line in response.aiter_lines():
                    if line.startswith("data:"):
                        payload = line[len("data:"):].strip()
                        if payload:
                            event = json.loads(payload)
                            if event.get("type") == "hello":
                                found_event.append(event)
                                break

        task = asyncio.create_task(read_stream())
        await asyncio.sleep(0.02)  # let the subscriber register itself

        bus.publish({"type": "hello", "msg": "world"})
        # Stop the body generator so the response completes cleanly.
        bus.publish({"type": "run.complete", "run_id": run_id})
        await asyncio.wait_for(task, timeout=5)

        assert len(found_event) == 1
        assert found_event[0]["msg"] == "world"


@pytest.mark.asyncio
async def test_stream_404_for_unknown_run(app_with_patched_runner):
    transport = httpx.ASGITransport(app=app_with_patched_runner)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/runs/does-not-exist/stream")
        assert resp.status_code == 404


@pytest.mark.asyncio
async def test_stream_stops_on_run_complete(app_with_patched_runner):
    transport = httpx.ASGITransport(app=app_with_patched_runner)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # Create a run
        resp = await client.post("/runs", json={"startup_idea": "x"})
        run_id = resp.json()["run_id"]
        bus = _registry.get(run_id)

        lines = []

        async def read_stream():
            async with client.stream("GET", f"/runs/{run_id}/stream") as response:
                async for line in response.aiter_lines():
                    lines.append(line)
                    if len(lines) >= 5:
                        break

        task = asyncio.create_task(read_stream())
        await asyncio.sleep(0.02)  # let the subscriber register itself

        bus.publish({"type": "run.complete", "run_id": run_id})
        await asyncio.wait_for(task, timeout=5)

        data_lines = [line for line in lines if line.startswith("data:")]
        assert len(data_lines) >= 1
