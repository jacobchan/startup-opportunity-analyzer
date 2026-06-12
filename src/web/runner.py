from src.deliberation.rounds import RoundOrchestrator
from src.storage import update_run_status, get_session


def run_deliberation(run_id: str, startup_idea: str, event_publisher) -> dict:
    """Execute 3-round deliberation and return final report dict."""
    from src.crew import StartupAnalyzerCrew

    crew = StartupAnalyzerCrew()
    orch = RoundOrchestrator(
        run_id=run_id,
        agents={},
        tasks={},
        event_publisher=event_publisher,
    )

    update_run_status(get_session(), run_id, "running")

    orch.transition_to("round1")
    r1_outputs = crew.run_round1(startup_idea=startup_idea, publisher=event_publisher)
    for agent_name, output in r1_outputs.items():
        orch.record_r1_output(agent_name, output)

    orch.transition_to("round2")
    r2_challenges = crew.run_round2(r1_outputs=r1_outputs, publisher=event_publisher)
    for ch in r2_challenges:
        orch.record_challenge(ch)

    orch.transition_to("round3")
    final_report = crew.run_round3(
        r1_outputs=r1_outputs, challenges=r2_challenges, publisher=event_publisher,
    )

    update_run_status(get_session(), run_id, "complete")
    event_publisher({"type": "run.complete", "run_id": run_id, "report": final_report})
    return final_report
