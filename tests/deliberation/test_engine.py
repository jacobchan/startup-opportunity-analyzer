"""Unit tests for DeliberationEngine.

The engine accepts an optional ``agent_factory`` that bypasses real
CrewAI Agent construction. We use that to inject MagicMock agents
and assert control flow (agent ordering, checkpoint writes, resume
from saved state) without invoking the LLM.
"""

import json
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.deliberation.engine import DeliberationEngine
from src.deliberation.state import (
    ROUND_1,
    ROUND_2,
    ROUND_3,
    ROUND_COMPLETE,
    ROUND_FAILED,
    ROUND_NONE,
    EngineState,
)
from src.storage import create_run
from src.storage.db import init_db


# ── fixtures ────────────────────────────────────────────


@pytest.fixture
def session_factory():
    eng = create_engine("sqlite:///:memory:")
    init_db(eng)
    Session = sessionmaker(bind=eng)
    return Session


@pytest.fixture
def run_id(session_factory):
    session = session_factory()
    try:
        run = create_run(session, startup_idea="AI Agent 平台")
        return run.run_id
    finally:
        session.close()


@pytest.fixture
def mock_llm():
    return MagicMock(name="LLM")


@pytest.fixture
def agents_config():
    return {
        "market_analyst": {"role": "市场分析师", "goal": "g", "backstory": "b"},
        "competitor_researcher": {"role": "竞品调研", "goal": "g", "backstory": "b"},
        "finance_analyst": {"role": "财务分析", "goal": "g", "backstory": "b"},
        "risk_reviewer": {"role": "风险评审", "goal": "g", "backstory": "b"},
        "strategy_advisor": {"role": "战略顾问", "goal": "g", "backstory": "b"},
    }


@pytest.fixture
def tasks_config():
    return {
        "market_analysis": {"description": "市场：{startup_idea}", "expected_output": "json"},
        "competitor_analysis": {"description": "竞品：{startup_idea}", "expected_output": "json"},
        "finance_analysis": {"description": "财务：{startup_idea}", "expected_output": "json"},
        "risk_review": {"description": "风险：{startup_idea}", "expected_output": "json"},
        "strategy_report": {"description": "战略：{startup_idea}", "expected_output": "json"},
        "round2_challenge": {
            "description": "挑战：{startup_idea}\n\n{round1_outputs}",
            "expected_output": "json",
        },
    }


@pytest.fixture
def tools_map():
    return {
        "market_analyst": [MagicMock(name="search")],
        "competitor_researcher": [MagicMock(name="search")],
        "finance_analyst": [MagicMock(name="search")],
        "risk_reviewer": [MagicMock(name="search")],
        "strategy_advisor": [],
    }


@pytest.fixture
def challenge_tool_factory():
    def _factory(run_id, agent_name, max_challenges=3):
        return MagicMock(name=f"challenge_tool_{agent_name}")
    return _factory


@pytest.fixture
def publisher():
    events = []
    def _pub(e):
        events.append(e)
    _pub.events = events
    return _pub


def _make_agent_factory(events_log):
    """Build an agent_factory that yields MagicMock agents and logs calls."""
    cache: dict = {}

    def factory(name: str, tools_override):
        events_log.append(name)
        if tools_override is None and name in cache:
            return cache[name]
        a = MagicMock(name=f"agent_{name}")
        a.tools = tools_override if tools_override is not None else []
        if tools_override is None:
            cache[name] = a
        return a

    return factory


@pytest.fixture(autouse=True)
def patch_crewai_task():
    """CrewAI Task does strict Pydantic validation on agent=...; bypass it
    by mocking the entire Task class. Tests already mock Crew."""
    with patch("src.deliberation.engine.Task") as MockTask:
        MockTask.side_effect = lambda **kwargs: MagicMock(description=kwargs.get("description"))
        yield MockTask


def _fake_crew_result(payload=None):
    if payload is None:
        payload = {"x": 1}
    r = MagicMock()
    r.raw = json.dumps(payload, ensure_ascii=False)
    return r


def _build_engine(
    session_factory, run_id, mock_llm, agents_config, tasks_config,
    tools_map, challenge_tool_factory, publisher, agent_log,
):
    """Standard engine builder with mock agent factory."""
    return DeliberationEngine(
        run_id=run_id,
        startup_idea="AI Agent 平台",
        llm=mock_llm,
        agents_config=agents_config,
        tasks_config=tasks_config,
        tools_map=tools_map,
        challenge_tool_factory=challenge_tool_factory,
        publisher=publisher,
        session_factory=session_factory,
        agent_factory=_make_agent_factory(agent_log),
    )


# ── core flow tests ────────────────────────────────────


def test_engine_full_run_calls_all_agents_in_order(
    session_factory, run_id, mock_llm, agents_config, tasks_config,
    tools_map, challenge_tool_factory, publisher,
):
    agent_log: list[str] = []
    with patch("src.deliberation.engine.Crew") as MockCrew:
        MockCrew.return_value.kickoff.return_value = _fake_crew_result({"ok": True})
        engine = _build_engine(
            session_factory, run_id, mock_llm, agents_config, tasks_config,
            tools_map, challenge_tool_factory, publisher, agent_log,
        )
        report = engine.run_all()

    assert agent_log == [
        "market_analyst", "competitor_researcher", "finance_analyst", "risk_reviewer",
        "market_analyst", "competitor_researcher", "finance_analyst",
        "strategy_advisor",
    ]
    assert report == {"ok": True}
    assert engine.state.current_round == ROUND_COMPLETE


def test_engine_persists_state_after_each_agent(
    session_factory, run_id, mock_llm, agents_config, tasks_config,
    tools_map, challenge_tool_factory, publisher,
):
    agent_log: list[str] = []
    with patch("src.deliberation.engine.Crew") as MockCrew:
        MockCrew.return_value.kickoff.return_value = _fake_crew_result({"x": 1})
        engine = _build_engine(
            session_factory, run_id, mock_llm, agents_config, tasks_config,
            tools_map, challenge_tool_factory, publisher, agent_log,
        )
        engine.run_all()

    from src.deliberation.checkpoint import CheckpointStore
    loaded = CheckpointStore(session_factory).load(run_id)
    assert loaded is not None
    assert loaded.current_round == ROUND_COMPLETE
    assert set(loaded.r1_completed_agents) == {
        "market_analyst", "competitor_researcher", "finance_analyst", "risk_reviewer",
    }
    assert loaded.r3_report == {"x": 1}


# ── resume tests ───────────────────────────────────────


def test_engine_resume_from_round1_after_market_completes(
    session_factory, run_id, mock_llm, agents_config, tasks_config,
    tools_map, challenge_tool_factory, publisher,
):
    from src.deliberation.checkpoint import CheckpointStore
    store = CheckpointStore(session_factory)
    state = store.init_fresh(run_id, "AI Agent 平台")
    state.current_round = ROUND_1
    state.r1_outputs = {"market_analyst": {"tam": "100亿"}}
    state.r1_completed_agents = ["market_analyst"]
    store.save(state)

    agent_log: list[str] = []
    with patch("src.deliberation.engine.Crew") as MockCrew:
        MockCrew.return_value.kickoff.return_value = _fake_crew_result({"r": "ok"})
        engine = _build_engine(
            session_factory, run_id, mock_llm, agents_config, tasks_config,
            tools_map, challenge_tool_factory, publisher, agent_log,
        )
        engine.resume()

    # market_analyst R1 was already done; should only appear once (R2 challenge)
    assert agent_log.count("market_analyst") == 1
    assert agent_log == [
        "competitor_researcher", "finance_analyst", "risk_reviewer",  # R1 remaining
        "market_analyst", "competitor_researcher", "finance_analyst",  # R2 all 3
        "strategy_advisor",
    ]
    assert engine.state.current_round == ROUND_COMPLETE


def test_engine_resume_from_round2_picks_up_at_competitor(
    session_factory, run_id, mock_llm, agents_config, tasks_config,
    tools_map, challenge_tool_factory, publisher,
):
    from src.deliberation.checkpoint import CheckpointStore
    store = CheckpointStore(session_factory)
    state = store.init_fresh(run_id, "x")
    state.current_round = ROUND_2
    state.r1_outputs = {
        "market_analyst": {"tam": "100"},
        "competitor_researcher": {"c": 1},
        "finance_analyst": {"f": 1},
        "risk_reviewer": {"r": 1},
    }
    state.r1_completed_agents = [
        "market_analyst", "competitor_researcher", "finance_analyst", "risk_reviewer",
    ]
    state.r2_completed_agents = ["market_analyst"]
    store.save(state)

    agent_log: list[str] = []
    with patch("src.deliberation.engine.Crew") as MockCrew:
        MockCrew.return_value.kickoff.return_value = _fake_crew_result({"r": "ok"})
        engine = _build_engine(
            session_factory, run_id, mock_llm, agents_config, tasks_config,
            tools_map, challenge_tool_factory, publisher, agent_log,
        )
        engine.resume()

    # No R1 agents, no R2 market
    assert "market_analyst" not in agent_log
    assert "risk_reviewer" not in agent_log
    assert agent_log == ["competitor_researcher", "finance_analyst", "strategy_advisor"]
    assert engine.state.current_round == ROUND_COMPLETE


def test_engine_resume_complete_run_returns_cached_report(
    session_factory, run_id, mock_llm, agents_config, tasks_config,
    tools_map, challenge_tool_factory, publisher,
):
    from src.deliberation.checkpoint import CheckpointStore
    store = CheckpointStore(session_factory)
    state = store.init_fresh(run_id, "x")
    state.current_round = ROUND_COMPLETE
    state.r3_report = {"decision": "Go", "summary": "yes"}
    store.save(state)

    agent_log: list[str] = []
    with patch("src.deliberation.engine.Crew") as MockCrew:
        MockCrew.return_value.kickoff.return_value = _fake_crew_result()
        engine = _build_engine(
            session_factory, run_id, mock_llm, agents_config, tasks_config,
            tools_map, challenge_tool_factory, publisher, agent_log,
        )
        result = engine.resume()

    assert result == {"decision": "Go", "summary": "yes"}
    assert agent_log == []  # no agents created at all


def test_engine_resume_failed_run_raises(
    session_factory, run_id, mock_llm, agents_config, tasks_config,
    tools_map, challenge_tool_factory, publisher,
):
    from src.deliberation.checkpoint import CheckpointStore
    store = CheckpointStore(session_factory)
    state = store.init_fresh(run_id, "x")
    state.current_round = ROUND_FAILED
    state.error = "boom"
    store.save(state)

    agent_log: list[str] = []
    with patch("src.deliberation.engine.Crew"):
        engine = _build_engine(
            session_factory, run_id, mock_llm, agents_config, tasks_config,
            tools_map, challenge_tool_factory, publisher, agent_log,
        )
        with pytest.raises(RuntimeError, match="boom"):
            engine.resume()


# ── agent cache tests ──────────────────────────────────


def test_agent_cache_returns_same_instance_for_same_name(
    session_factory, run_id, mock_llm, agents_config, tasks_config,
    tools_map, challenge_tool_factory, publisher,
):
    agent_log: list[str] = []
    with patch("src.deliberation.engine.Crew"):
        engine = _build_engine(
            session_factory, run_id, mock_llm, agents_config, tasks_config,
            tools_map, challenge_tool_factory, publisher, agent_log,
        )
        a1 = engine._get_agent("market_analyst")
        a2 = engine._get_agent("market_analyst")
        assert a1 is a2
        b1 = engine._get_agent("competitor_researcher")
        assert b1 is not a1


def test_agent_cache_isolated_when_tools_override_given(
    session_factory, run_id, mock_llm, agents_config, tasks_config,
    tools_map, challenge_tool_factory, publisher,
):
    agent_log: list[str] = []
    with patch("src.deliberation.engine.Crew"):
        engine = _build_engine(
            session_factory, run_id, mock_llm, agents_config, tasks_config,
            tools_map, challenge_tool_factory, publisher, agent_log,
        )
        cached = engine._get_agent("market_analyst")
        override_tool = MagicMock(name="challenge_tool")
        with_override = engine._get_agent("market_analyst", tools_override=[override_tool])
        # Override must NOT pollute cache
        assert cached is not with_override
        # Cache still returns no-override instance
        assert engine._get_agent("market_analyst") is cached
        assert with_override.tools == [override_tool]


# ── event ordering ─────────────────────────────────────


def test_engine_emits_expected_event_sequence(
    session_factory, run_id, mock_llm, agents_config, tasks_config,
    tools_map, challenge_tool_factory, publisher,
):
    agent_log: list[str] = []
    with patch("src.deliberation.engine.Crew") as MockCrew:
        MockCrew.return_value.kickoff.return_value = _fake_crew_result()
        engine = _build_engine(
            session_factory, run_id, mock_llm, agents_config, tasks_config,
            tools_map, challenge_tool_factory, publisher, agent_log,
        )
        engine.run_all()

    types = [e.get("type") for e in publisher.events]
    assert types[0] == "round.transition"
    agent_starts = [e for e in publisher.events if e["type"] == "agent.start"]
    agent_ends = [e for e in publisher.events if e["type"] == "agent.end"]
    assert len(agent_starts) == 8
    assert len(agent_ends) == 8
    transitions = [e["to_round"] for e in publisher.events if e["type"] == "round.transition"]
    assert transitions == ["round1", "round2", "round3"]


# ── failure handling ───────────────────────────────────


def test_engine_marks_failed_on_exception(
    session_factory, run_id, mock_llm, agents_config, tasks_config,
    tools_map, challenge_tool_factory, publisher,
):
    agent_log: list[str] = []
    def boom(agents, tasks, verbose=True):
        crew = MagicMock()
        crew.kickoff.side_effect = RuntimeError("LLM timeout")
        return crew

    with patch("src.deliberation.engine.Crew", side_effect=boom):
        engine = _build_engine(
            session_factory, run_id, mock_llm, agents_config, tasks_config,
            tools_map, challenge_tool_factory, publisher, agent_log,
        )
        with pytest.raises(RuntimeError, match="LLM timeout"):
            engine.run_all()

    from src.deliberation.checkpoint import CheckpointStore
    loaded = CheckpointStore(session_factory).load(run_id)
    assert loaded.current_round == ROUND_FAILED
    assert "LLM timeout" in loaded.error
