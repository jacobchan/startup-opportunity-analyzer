"""Tests for the in-process SSE bus registry."""

from src.web.run_registry import RunRegistry


def test_registry_create_and_get():
    r = RunRegistry()
    bus = r.create("run-1")
    assert r.get("run-1") is bus
    assert r.get("run-2") is None


def test_registry_release_drops_bus():
    r = RunRegistry()
    r.create("run-1")
    r.release("run-1")
    assert r.get("run-1") is None
    # Releasing again is a no-op
    r.release("run-1")
    assert r.get("run-1") is None


def test_registry_create_overwrites_existing():
    """Resuming a run creates a fresh bus. We expect the prior bus to
    be replaced (with a warning in production) so the SSE consumer
    connects to the right one.
    """
    r = RunRegistry()
    bus1 = r.create("run-1")
    bus2 = r.create("run-1")
    assert r.get("run-1") is bus2
    assert bus1 is not bus2


def test_registry_len():
    r = RunRegistry()
    assert len(r) == 0
    r.create("a")
    r.create("b")
    assert len(r) == 2
    r.release("a")
    assert len(r) == 1
