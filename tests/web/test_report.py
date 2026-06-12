import pytest
from fastapi.testclient import TestClient

from src.web.app import create_app
from src.storage import get_session, update_run_status
from src.storage.repository import _set_final_report_for_test


@pytest.fixture
def client(monkeypatch):
    def mock_runner(run_id, startup_idea, bus):
        pass
    monkeypatch.setattr("src.web.routes.runs._run_in_background", mock_runner)
    return TestClient(create_app())


def test_get_report_returns_final_report(client):
    resp = client.post("/runs", json={"startup_idea": "x"})
    run_id = resp.json()["run_id"]
    update_run_status(get_session(), run_id, "complete")
    _set_final_report_for_test(run_id, {"decision": "Go", "executive_summary": "ok"})

    resp2 = client.get(f"/runs/{run_id}/report")
    assert resp2.status_code == 200
    data = resp2.json()
    assert data["decision"] == "Go"


def test_get_report_404_for_unknown_run(client):
    resp = client.get("/runs/nonexistent/report")
    assert resp.status_code == 404


def test_get_report_409_for_running_run(client):
    resp = client.post("/runs", json={"startup_idea": "x"})
    run_id = resp.json()["run_id"]
    resp2 = client.get(f"/runs/{run_id}/report")
    assert resp2.status_code == 409
