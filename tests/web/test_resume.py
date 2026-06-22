"""Tests for POST /runs/{id}/resume."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from src.web.app import create_app
from src.storage import create_run, get_session


@pytest.fixture
def client():
    # Make sure DB is initialized for the test session
    from src.storage.db import init_db
    init_db()
    return TestClient(create_app())


def test_resume_endpoint_returns_202_for_paused_run(client):
    # Create a run directly (faster than going through POST /runs)
    session = get_session()
    try:
        run = create_run(session, startup_idea="AI Agent")
        run_id = run.run_id
    finally:
        session.close()

    with patch("src.web.routes.resume.resume_deliberation") as mock_resume, \
         patch("src.web.routes.runs._run_in_background", lambda *a: None):
        mock_resume.return_value = {"decision": "Go"}
        resp = client.post(f"/runs/{run_id}/resume")
    assert resp.status_code == 200
    body = resp.json()
    assert body["run_id"] == run_id
    assert body["status"] == "resuming"


def test_resume_endpoint_404_for_unknown_run(client):
    resp = client.post("/runs/no-such-id/resume")
    assert resp.status_code == 404


def test_resume_endpoint_409_for_complete_run(client):
    session = get_session()
    try:
        run = create_run(session, startup_idea="x")
        run.status = "complete"
        from datetime import datetime, timezone
        run.completed_at = datetime.now(timezone.utc)
        run_id = run.run_id
        session.commit()
    finally:
        session.close()

    resp = client.post(f"/runs/{run_id}/resume")
    assert resp.status_code == 409
    assert "complete" in resp.json()["detail"]


def test_resume_endpoint_409_for_already_running_run(client):
    session = get_session()
    try:
        run = create_run(session, startup_idea="x")
        run.status = "running"
        run_id = run.run_id
        session.commit()
    finally:
        session.close()

    resp = client.post(f"/runs/{run_id}/resume")
    assert resp.status_code == 409


def test_resume_endpoint_works_for_failed_run(client):
    session = get_session()
    try:
        run = create_run(session, startup_idea="x")
        run.status = "failed"
        run.error = "LLM timeout"
        run_id = run.run_id
        session.commit()
    finally:
        session.close()

    with patch("src.web.routes.resume.resume_deliberation") as mock_resume, \
         patch("src.web.routes.runs._run_in_background", lambda *a: None):
        mock_resume.return_value = {"decision": "Conditional-Go"}
        resp = client.post(f"/runs/{run_id}/resume")
    assert resp.status_code == 200
    assert resp.json()["status"] == "resuming"
