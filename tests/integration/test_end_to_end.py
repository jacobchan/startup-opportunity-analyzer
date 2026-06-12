import asyncio
import json
import time
from unittest.mock import MagicMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient

from src.web.app import create_app
from src.web.run_registry import registry
from src.storage import get_run, get_session


MOCK_R1_OUTPUTS = {
    "market_analyst": {
        "startup_idea": "test",
        "tam_sam_som": {"tam": {"value": "100亿", "source": "x", "year": "2024"}},
    },
    "competitor_researcher": {"startup_idea": "test", "competitors": []},
    "finance_analyst": {"startup_idea": "test", "ltv_analysis": {"estimated_ltv": "X"}},
    "risk_reviewer": {"startup_idea": "test", "risks": []},
}

MOCK_R2_CHALLENGES = [
    {
        "challenge_id": "ch-1", "issuer": "market_analyst",
        "target": "finance_analyst", "claim": "LTV 假设过高",
        "reason": "行业基准是 Y", "response": "已调整", "verdict": "modified",
    },
]

MOCK_R3_REPORT = {
    "startup_idea": "test",
    "decision": "Conditional-Go",
    "executive_summary": "需要进一步验证",
    "final_confidence": "中",
}


def test_end_to_end_run_completes_with_report():
    with patch("src.crew.StartupAnalyzerCrew") as MockCrew:
        instance = MagicMock()
        instance.run_round1.return_value = MOCK_R1_OUTPUTS
        instance.run_round2.return_value = MOCK_R2_CHALLENGES
        instance.run_round3.return_value = MOCK_R3_REPORT
        MockCrew.return_value = instance

        client = TestClient(create_app())

        resp = client.post("/runs", json={"startup_idea": "AI Agent 平台"})
        assert resp.status_code == 200
        run_id = resp.json()["run_id"]

        # Wait for background task to complete (max 5 seconds)
        for _ in range(50):
            run = get_run(get_session(), run_id)
            if run.status == "complete":
                break
            time.sleep(0.1)

        run = get_run(get_session(), run_id)
        assert run.status == "complete", f"Expected complete, got {run.status}"
        assert run.final_report is not None
        assert run.final_report["decision"] == "Conditional-Go"


@pytest.mark.asyncio
async def test_end_to_end_sse_stream_emits_events():
    with patch("src.crew.StartupAnalyzerCrew") as MockCrew:
        instance = MagicMock()
        instance.run_round1.return_value = {}
        instance.run_round2.return_value = []
        instance.run_round3.return_value = {"decision": "Go"}
        MockCrew.return_value = instance

        app = create_app()
        transport = httpx.ASGITransport(app=app)

        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            # Create a run
            resp = await client.post("/runs", json={"startup_idea": "x"})
            run_id = resp.json()["run_id"]
            bus = registry.get(run_id)
            assert bus is not None

            received_types = []

            async def read_stream():
                async with client.stream("GET", f"/runs/{run_id}/stream") as response:
                    async for line in response.aiter_lines():
                        if line.startswith("data:"):
                            payload = line[len("data:"):].strip()
                            if payload:
                                event = json.loads(payload)
                                received_types.append(event.get("type"))
                                if "run.complete" in received_types:
                                    break

            task = asyncio.create_task(read_stream())
            await asyncio.sleep(0.05)  # let the subscriber register itself

            bus.publish({"type": "test.event", "msg": "a"})
            bus.publish({"type": "run.complete", "run_id": run_id})

            await asyncio.wait_for(task, timeout=5)

        assert "test.event" in received_types, f"Got: {received_types}"
        assert "run.complete" in received_types, f"Got: {received_types}"
