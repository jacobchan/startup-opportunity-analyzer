import pytest
from fastapi.testclient import TestClient

from src.web.app import create_app


@pytest.fixture
def client(monkeypatch):
    # Monkeypatch the background runner to skip real execution
    def mock_runner(run_id, startup_idea, bus):
        pass
    monkeypatch.setattr("src.web.routes.runs._run_in_background", mock_runner)
    return TestClient(create_app())


def test_post_runs_creates_run_and_returns_id(client):
    resp = client.post("/runs", json={"startup_idea": "AI Agent 平台"})
    assert resp.status_code == 200
    data = resp.json()
    assert "run_id" in data
    assert data["status"] == "queued"


def test_get_run_returns_status(client):
    resp = client.post("/runs", json={"startup_idea": "x"})
    run_id = resp.json()["run_id"]
    resp2 = client.get(f"/runs/{run_id}")
    assert resp2.status_code == 200
    assert resp2.json()["run_id"] == run_id
    assert resp2.json()["status"] in ("queued", "running", "complete")


def test_get_run_404(client):
    resp = client.get("/runs/nonexistent-id")
    assert resp.status_code == 404


def test_post_runs_validates_input(client):
    resp = client.post("/runs", json={})
    assert resp.status_code == 422
