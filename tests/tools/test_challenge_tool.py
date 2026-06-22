"""Unit tests for the multi-action ChallengeTool."""

from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.storage import create_run, get_challenge
from src.storage.db import init_db
from src.tools.challenge_tool import (
    make_challenge_tool,
)


# ── in-memory DB fixture ───────────────────────────────


@pytest.fixture
def session_factory():
    # StaticPool forces every Session() to share the same underlying
    # connection, so an :memory: SQLite is visible across calls.
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    init_db(eng)
    Session = sessionmaker(bind=eng)
    return Session


@pytest.fixture
def run_id(session_factory):
    session = session_factory()
    try:
        run = create_run(session, startup_idea="idea")
        return run.run_id
    finally:
        session.close()


@pytest.fixture
def in_memory_session(session_factory, monkeypatch):
    """Route challenge_tool.get_session() to the in-memory engine.

    The tool's repository helpers take a session via get_session() which by
    default points at the on-disk ``data/analyzer.db``. In tests we want all
    reads and writes to hit the in-memory SQLite the fixture already created.
    We monkeypatch the symbol **imported into the tool module** so both the
    tool and its calls into the repository layer share the same engine.
    """
    from src.tools import challenge_tool as ct

    Session = session_factory

    def _factory():
        return Session()

    monkeypatch.setattr(ct, "get_session", _factory)

    def _patch_repo(name):
        mod = ct
        # The tool imports the repository functions by name; we don't need
        # to patch those because they take an explicit session argument and
        # the tool now hands them the in-memory session. So nothing to do
        # here beyond confirming the symbol is reachable.
        assert hasattr(mod, name), f"tool module missing {name}"

    for name in ("add_challenge", "update_challenge_response",
                 "get_unresolved_challenges_for_run"):
        _patch_repo(name)

    return Session


# ── legacy issue-action tests (kept verbatim) ──────────


def test_challenge_tool_has_correct_name():
    tool = make_challenge_tool(run_id="run-1", agent_name="market_analyst")
    assert tool.name == "challenge"


def test_challenge_tool_routes_to_target(run_id):
    mock_session = MagicMock()
    mock_add = MagicMock(return_value=MagicMock(challenge_id="ch-1"))

    with patch("src.tools.challenge_tool.get_session", return_value=mock_session), \
         patch("src.tools.challenge_tool.add_challenge", mock_add):
        tool = make_challenge_tool(run_id=run_id, agent_name="market_analyst")
        result = tool._run(
            action="challenge",
            target="finance_analyst",
            claim="LTV 假设过高",
            reason="行业基准是 X",
        )
        assert "ch-1" in result
        mock_add.assert_called_once()
        args, kwargs = mock_add.call_args
        assert kwargs["issuer"] == "market_analyst"
        assert kwargs["target"] == "finance_analyst"


def test_challenge_tool_validates_not_self_challenge():
    tool = make_challenge_tool(run_id="run-1", agent_name="market_analyst")
    with pytest.raises(ValueError, match="yourself"):
        tool._run(
            action="challenge",
            target="market_analyst", claim="x", reason="y",
        )


def test_challenge_tool_validates_non_empty_claim():
    tool = make_challenge_tool(run_id="run-1", agent_name="market_analyst")
    with pytest.raises(ValueError, match="claim"):
        tool._run(
            action="challenge",
            target="finance_analyst", claim="", reason="y",
        )


def test_challenge_tool_max_challenges_per_agent(run_id):
    tool = make_challenge_tool(
        run_id=run_id, agent_name="market_analyst", max_challenges=2,
    )
    with patch("src.tools.challenge_tool.get_session", return_value=MagicMock()), \
         patch("src.tools.challenge_tool.add_challenge", return_value=MagicMock(challenge_id="x")):
        tool._run(action="challenge", target="finance_analyst", claim="a", reason="r")
        tool._run(action="challenge", target="risk_reviewer", claim="b", reason="r")
        with pytest.raises(RuntimeError, match="max challenges"):
            tool._run(action="challenge", target="competitor_researcher", claim="c", reason="r")


# ── new behavior: max_challenges=0 disables issue ─────


def test_challenge_tool_max_zero_disables_issue_action():
    tool = make_challenge_tool(run_id="run-1", agent_name="market_analyst", max_challenges=0)
    with pytest.raises(RuntimeError, match="disabled"):
        tool._run(action="challenge", target="x", claim="c", reason="r")


# ── new behavior: respond action ───────────────────────


def test_respond_action_persists_response_and_verdict(run_id, session_factory):
    # Seed a challenge directly via the repository
    from src.storage import add_challenge
    s = session_factory()
    try:
        ch = add_challenge(
            session=s, run_id=run_id,
            issuer="market_analyst", target="finance_analyst",
            claim="LTV 假设过高", reason="无依据",
        )
        cid = ch.challenge_id
    finally:
        s.close()

    tool = make_challenge_tool(run_id=run_id, agent_name="finance_analyst")
    out = tool._run(
        action="respond",
        challenge_id=cid,
        response="已修正为 X",
        verdict="modified",
    )
    assert "modified" in out

    s = session_factory()
    try:
        ch = get_challenge(session=s, challenge_id=cid)
        assert ch.response == "已修正为 X"
        assert ch.verdict == "modified"
        assert ch.resolved_at is not None
    finally:
        s.close()


def test_respond_action_does_not_consume_quota(run_id):
    tool = make_challenge_tool(
        run_id=run_id, agent_name="finance_analyst", max_challenges=1,
    )
    # Pre-fill the quota
    with patch("src.tools.challenge_tool.get_session", return_value=MagicMock()), \
         patch("src.tools.challenge_tool.add_challenge", return_value=MagicMock(challenge_id="x")):
        tool._run(action="challenge", target="market_analyst", claim="a", reason="r")
        assert tool._count == 1

    # Now respond; quota must NOT be consumed
    with patch("src.tools.challenge_tool.get_session", return_value=MagicMock()), \
         patch("src.tools.challenge_tool.update_challenge_response",
               return_value=MagicMock(challenge_id="x", target="finance_analyst")):
        tool._run(
            action="respond",
            challenge_id="x", response="r", verdict="accepted",
        )
    assert tool._count == 1  # unchanged


def test_respond_action_rejects_invalid_verdict():
    tool = make_challenge_tool(run_id="run-1", agent_name="finance_analyst")
    with pytest.raises(ValueError, match="verdict"):
        tool._run(
            action="respond",
            challenge_id="x", response="r", verdict="banana",
        )


def test_respond_action_rejects_empty_response():
    tool = make_challenge_tool(run_id="run-1", agent_name="finance_analyst")
    with pytest.raises(ValueError, match="response"):
        tool._run(
            action="respond",
            challenge_id="x", response="  ", verdict="accepted",
        )


def test_respond_action_rejects_wrong_target(run_id, session_factory):
    from src.storage import add_challenge
    s = session_factory()
    try:
        ch = add_challenge(
            session=s, run_id=run_id,
            issuer="market_analyst", target="finance_analyst",
            claim="LTV 假设过高", reason="无依据",
        )
        cid = ch.challenge_id
    finally:
        s.close()

    # market_analyst is the wrong issuer here
    tool = make_challenge_tool(run_id=run_id, agent_name="market_analyst")
    with pytest.raises(ValueError, match="targets"):
        tool._run(
            action="respond",
            challenge_id=cid, response="x", verdict="accepted",
        )


# ── new behavior: list_open action ────────────────────


def test_list_open_returns_only_unresolved_targeting_self(run_id, session_factory):
    from src.storage import add_challenge, update_challenge_response
    s = session_factory()
    try:
        # 2 unresolved targeting finance_analyst
        add_challenge(
            session=s, run_id=run_id,
            issuer="market_analyst", target="finance_analyst",
            claim="c1", reason="r1",
        )
        add_challenge(
            session=s, run_id=run_id,
            issuer="competitor_researcher", target="finance_analyst",
            claim="c2", reason="r2",
        )
        # 1 already resolved
        ch3 = add_challenge(
            session=s, run_id=run_id,
            issuer="market_analyst", target="finance_analyst",
            claim="c3", reason="r3",
        )
        update_challenge_response(
            session=s, challenge_id=ch3.challenge_id,
            response="r", verdict="rejected",
        )
        # 1 targeting a different agent
        add_challenge(
            session=s, run_id=run_id,
            issuer="market_analyst", target="competitor_researcher",
            claim="c4", reason="r4",
        )
    finally:
        s.close()

    tool = make_challenge_tool(run_id=run_id, agent_name="finance_analyst")
    open_challenges = tool._run(action="list_open", target="finance_analyst")
    assert isinstance(open_challenges, list)
    assert len(open_challenges) == 2
    claims = {c["claim"] for c in open_challenges}
    assert claims == {"c1", "c2"}


def test_list_open_rejects_wrong_target():
    tool = make_challenge_tool(run_id="run-1", agent_name="finance_analyst")
    with pytest.raises(ValueError, match="self.issuer"):
        tool._run(action="list_open", target="market_analyst")


def test_list_open_does_not_consume_quota():
    tool = make_challenge_tool(run_id="run-1", agent_name="finance_analyst", max_challenges=1)
    with patch("src.tools.challenge_tool.get_session", return_value=MagicMock()):
        tool._run(action="list_open", target="finance_analyst")
    assert tool._count == 0


# ── new behavior: unknown action ──────────────────────


def test_unknown_action_raises():
    tool = make_challenge_tool(run_id="run-1", agent_name="market_analyst")
    with pytest.raises(ValueError, match="unknown action"):
        tool._run(action="surprise")
