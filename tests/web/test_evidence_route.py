from fastapi.testclient import TestClient

from src.web.app import create_app
from src.storage import add_evidence, get_session


def test_get_evidence_returns_content():
    client = TestClient(create_app())
    ev = add_evidence(
        session=get_session(),
        run_id="run-1",
        source_type="search",
        query="AI Agent",
        url="https://example.com",
        title="报告",
        content_excerpt="前 500 字",
        url_hash="hash1",
    )
    resp = client.get(f"/evidence/{ev.evidence_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["evidence_id"] == ev.evidence_id
    assert data["title"] == "报告"
    assert data["content_excerpt"] == "前 500 字"


def test_get_evidence_404():
    client = TestClient(create_app())
    resp = client.get("/evidence/nonexistent")
    assert resp.status_code == 404
