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


def test_list_runs_returns_recent_items(client):
    ids = []
    for idea in ["idea-a", "idea-b", "idea-c"]:
        resp = client.post("/runs", json={"startup_idea": idea})
        ids.append(resp.json()["run_id"])
    resp = client.get("/runs?limit=10&offset=0")
    assert resp.status_code == 200
    data = resp.json()
    assert "runs" in data
    assert "total" in data
    assert data["total"] >= 3
    assert data["runs"][0]["startup_idea"] == "idea-c"


def test_list_runs_defaults_limit_10_offset_0(client):
    resp = client.get("/runs")
    assert resp.status_code == 200
    data = resp.json()
    assert "runs" in data
    assert "total" in data


def test_delete_run_removes_run(client):
    resp = client.post("/runs", json={"startup_idea": "x"})
    run_id = resp.json()["run_id"]
    del_resp = client.delete(f"/runs/{run_id}")
    assert del_resp.status_code == 204
    get_resp = client.get(f"/runs/{run_id}")
    assert get_resp.status_code == 404


def test_delete_run_404_for_unknown(client):
    resp = client.delete("/runs/no-such-id")
    assert resp.status_code == 404
