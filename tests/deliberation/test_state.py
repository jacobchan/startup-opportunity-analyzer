"""Unit tests for EngineState and CheckpointStore."""

import json
import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.deliberation.checkpoint import CheckpointStore
from src.deliberation.state import (
    ROUND_1,
    ROUND_2,
    ROUND_3,
    ROUND_COMPLETE,
    ROUND_FAILED,
    ROUND_NONE,
    EngineState,
)
from src.storage.db import init_db


@pytest.fixture
def session_factory():
    eng = create_engine("sqlite:///:memory:")
    init_db(eng)
    Session = sessionmaker(bind=eng)
    return Session


def test_state_starts_at_none():
    s = EngineState(run_id="r1", startup_idea="idea")
    assert s.current_round == ROUND_NONE
    assert s.r1_outputs == {}
    assert s.r1_completed_agents == []
    assert s.r2_challenges == []
    assert s.r3_report is None


def test_state_is_resumable():
    for r in (ROUND_1, ROUND_2, ROUND_3):
        s = EngineState(run_id="r", startup_idea="i", current_round=r)
        assert s.is_resumable() is True
    for r in (ROUND_NONE, ROUND_COMPLETE, ROUND_FAILED):
        s = EngineState(run_id="r", startup_idea="i", current_round=r)
        assert s.is_resumable() is False


def test_state_is_terminal():
    s = EngineState(run_id="r", startup_idea="i", current_round=ROUND_COMPLETE)
    assert s.is_terminal() is True
    s2 = EngineState(run_id="r", startup_idea="i", current_round=ROUND_FAILED)
    assert s2.is_terminal() is True
    s3 = EngineState(run_id="r", startup_idea="i", current_round=ROUND_1)
    assert s3.is_terminal() is False


def test_state_serialization_round_trip():
    s = EngineState(
        run_id="r1",
        startup_idea="AI Agent",
        current_round=ROUND_1,
        r1_outputs={"market_analyst": {"tam": "100亿"}},
        r1_completed_agents=["market_analyst"],
    )
    payload = s.model_dump(mode="json")
    # Must be JSON-serializable for SQLite JSON column
    json.dumps(payload)
    s2 = EngineState.model_validate(payload)
    assert s2.r1_outputs == s.r1_outputs
    assert s2.r1_completed_agents == ["market_analyst"]


def test_checkpoint_init_fresh_persists_state(session_factory):
    store = CheckpointStore(session_factory)
    run_id = f"run-{uuid.uuid4().hex[:8]}"
    # Need a Run row first (FK-like usage) - create manually
    from src.storage import create_run
    session = session_factory()
    try:
        run = create_run(session, startup_idea="idea")
        run_id = run.run_id
    finally:
        session.close()

    state = store.init_fresh(run_id, "AI Agent 平台")
    assert state.run_id == run_id
    assert state.current_round == ROUND_NONE
    # Reload from DB
    loaded = store.load(run_id)
    assert loaded is not None
    assert loaded.startup_idea == "AI Agent 平台"


def test_checkpoint_save_updates_persisted_state(session_factory):
    from src.storage import create_run
    session = session_factory()
    try:
        run = create_run(session, startup_idea="idea")
        run_id = run.run_id
    finally:
        session.close()

    store = CheckpointStore(session_factory)
    state = store.init_fresh(run_id, "idea")
    state.current_round = ROUND_1
    state.r1_outputs = {"market_analyst": {"tam": "100亿"}}
    state.r1_completed_agents = ["market_analyst"]
    store.save(state)

    loaded = store.load(run_id)
    assert loaded.current_round == ROUND_1
    assert loaded.r1_outputs == {"market_analyst": {"tam": "100亿"}}


def test_checkpoint_load_returns_none_for_unknown_run(session_factory):
    store = CheckpointStore(session_factory)
    assert store.load("nonexistent") is None
