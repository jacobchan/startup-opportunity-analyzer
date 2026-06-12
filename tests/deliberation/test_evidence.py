import hashlib
from unittest.mock import MagicMock

from src.deliberation.evidence import evidence_capture, hash_url, make_evidence_id


def test_hash_url_stable():
    h1 = hash_url("https://example.com/article?x=1")
    h2 = hash_url("https://example.com/article?x=1")
    assert h1 == h2
    assert len(h1) == 32


def test_hash_url_different():
    assert hash_url("https://a.com") != hash_url("https://b.com")


def test_make_evidence_id_unique():
    ids = {make_evidence_id() for _ in range(100)}
    assert len(ids) == 100


def test_evidence_capture_writes_to_session(monkeypatch):
    mock_session = MagicMock()
    mock_add = MagicMock(return_value=MagicMock(evidence_id="ev-test"))
    monkeypatch.setattr("src.deliberation.evidence.add_evidence", mock_add)
    monkeypatch.setattr("src.deliberation.evidence.get_session", lambda: mock_session)

    @evidence_capture(run_id="run-1", source_type="search")
    def fake_search(query: str) -> str:
        return f"results for {query}"

    result = fake_search("AI Agent")
    assert result is not None
    assert "AI Agent" in result
    mock_add.assert_called_once()
    args, kwargs = mock_add.call_args
    assert kwargs["run_id"] == "run-1"
    assert kwargs["query"] == "AI Agent"
    assert kwargs["url_hash"] == hashlib.md5("AI Agent".encode()).hexdigest()


def test_evidence_capture_dedups(monkeypatch):
    same_evidence = MagicMock(evidence_id="ev-same")
    mock_add = MagicMock(return_value=same_evidence)
    monkeypatch.setattr("src.deliberation.evidence.add_evidence", mock_add)

    @evidence_capture(run_id="run-1", source_type="search")
    def fake_search(query: str) -> str:
        return "x"

    fake_search("same query")
    fake_search("same query")
    assert mock_add.call_count == 1
