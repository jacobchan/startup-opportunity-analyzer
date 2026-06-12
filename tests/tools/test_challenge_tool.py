from unittest.mock import MagicMock, patch

from src.tools.challenge_tool import make_challenge_tool


def test_challenge_tool_has_correct_name():
    tool = make_challenge_tool(run_id="run-1", agent_name="market_analyst")
    assert tool.name == "challenge"


def test_challenge_tool_routes_to_target():
    mock_session = MagicMock()
    mock_add = MagicMock(return_value=MagicMock(challenge_id="ch-1"))

    with patch("src.tools.challenge_tool.get_session", return_value=mock_session), \
         patch("src.tools.challenge_tool.add_challenge", mock_add):
        tool = make_challenge_tool(run_id="run-1", agent_name="market_analyst")
        result = tool._run(
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
    try:
        tool._run(target="market_analyst", claim="x", reason="y")
        assert False, "should have raised"
    except ValueError:
        pass


def test_challenge_tool_validates_non_empty_claim():
    tool = make_challenge_tool(run_id="run-1", agent_name="market_analyst")
    try:
        tool._run(target="finance_analyst", claim="", reason="y")
        assert False, "should have raised"
    except ValueError:
        pass


def test_challenge_tool_max_challenges_per_agent():
    tool = make_challenge_tool(
        run_id="run-1", agent_name="market_analyst", max_challenges=2,
    )
    with patch("src.tools.challenge_tool.get_session", return_value=MagicMock()), \
         patch("src.tools.challenge_tool.add_challenge", return_value=MagicMock(challenge_id="x")):
        tool._run(target="finance_analyst", claim="a", reason="r")
        tool._run(target="risk_reviewer", claim="b", reason="r")
        try:
            tool._run(target="competitor_researcher", claim="c", reason="r")
            assert False, "should have raised"
        except RuntimeError as e:
            assert "max challenges" in str(e)
