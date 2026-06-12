from unittest.mock import MagicMock

from src.deliberation.rounds import RoundOrchestrator


def test_round_orchestrator_starts_at_none():
    orch = RoundOrchestrator(
        run_id="run-1",
        agents={},
        tasks={},
        event_publisher=lambda e: None,
    )
    assert orch.current_round is None


def test_round_transition_emits_event():
    events = []
    orch = RoundOrchestrator(
        run_id="run-1",
        agents={},
        tasks={},
        event_publisher=events.append,
    )
    orch.transition_to("round1")
    assert orch.current_round == "round1"
    assert any(
        isinstance(e, dict) and e.get("type") == "round.transition" and e["to_round"] == "round1"
        for e in events
    )


def test_round_transition_to_round2():
    events = []
    orch = RoundOrchestrator("run-1", {}, {}, events.append)
    orch.transition_to("round1")
    orch.transition_to("round2")
    assert orch.current_round == "round2"


def test_round_transition_to_round3():
    events = []
    orch = RoundOrchestrator("run-1", {}, {}, events.append)
    orch.transition_to("round1")
    orch.transition_to("round2")
    orch.transition_to("round3")
    assert orch.current_round == "round3"


def test_round_transition_validates_order():
    orch = RoundOrchestrator("run-1", {}, {}, lambda e: None)
    try:
        orch.transition_to("round2")  # skip round1
        assert False, "should have raised"
    except ValueError:
        pass


def test_round_transition_unknown_round():
    orch = RoundOrchestrator("run-1", {}, {}, lambda e: None)
    try:
        orch.transition_to("zzz")
        assert False, "should have raised"
    except ValueError:
        pass


def test_round_orchestrator_tracks_r1_outputs():
    orch = RoundOrchestrator("run-1", {}, {}, lambda e: None)
    orch.transition_to("round1")
    orch.record_r1_output("market_analyst", {"tam": "100"})
    assert orch.r1_outputs["market_analyst"] == {"tam": "100"}


def test_round_orchestrator_tracks_challenges():
    orch = RoundOrchestrator("run-1", {}, {}, lambda e: None)
    orch.transition_to("round1")
    orch.transition_to("round2")
    orch.record_challenge({"challenge_id": "ch-1"})
    assert "ch-1" in orch.challenge_ids
