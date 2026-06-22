"""conftest: route challenge_tool.get_session() to the in-memory engine for all tests in this dir."""
import pytest


@pytest.fixture(autouse=True)
def _route_challenge_tool_session(monkeypatch, session_factory):
    from src.tools import challenge_tool as ct
    monkeypatch.setattr(ct, "get_session", session_factory)
