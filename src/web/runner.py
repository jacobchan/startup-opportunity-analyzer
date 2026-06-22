"""Background task runners for the web layer.

Two entry points:

- ``run_deliberation`` — fresh start. Used by ``POST /runs``.
- ``resume_deliberation`` — continue from a persisted checkpoint. Used
  by ``POST /runs/{id}/resume``.

Both build a ``DeliberationEngine`` and let it own the round transitions,
event publishing, and checkpoint writes. The runner's only job is to
update ``Run.status`` at the boundaries.
"""

from __future__ import annotations

from src.deliberation.engine import DeliberationEngine
from src.storage import update_run_status, get_session, get_run
from src.storage.models import Run
from src.crew import StartupAnalyzerCrew
from src.config.settings import build_llm
from crewai import LLM
from src.tools.search_tool import search_tool
from src.tools.web_scraper import scrape_tool
from src.tools.challenge_tool import make_challenge_tool


# ``_build_llm`` is a thin alias for the shared factory. Kept under its
# original name so existing tests that patch this symbol keep working.
def _build_llm() -> LLM:
    return build_llm()


def _build_engine(run_id: str, startup_idea: str, publisher) -> DeliberationEngine:
    """Assemble all engine dependencies.

    Pulls LLM, agent configs, task configs, and per-role tool lists from
    the existing ``StartupAnalyzerCrew`` class so the engine shares the
    same configuration as the hierarchical entry point.
    """
    # @CrewBase resolves yaml -> dict lazily on instance creation, so we
    # need a throwaway instance to read the configs.
    _probe = StartupAnalyzerCrew()
    agents_config = _probe.agents_config
    tasks_config = _probe.tasks_config

    tools_map = {
        "market_analyst": [search_tool, scrape_tool],
        "competitor_researcher": [search_tool, scrape_tool],
        "finance_analyst": [search_tool, scrape_tool],
        "risk_reviewer": [search_tool],
        "strategy_advisor": [],
    }

    def challenge_factory(run_id_: str, agent_name: str, max_challenges: int = 3):
        return make_challenge_tool(
            run_id=run_id_, agent_name=agent_name, max_challenges=max_challenges,
        )

    return DeliberationEngine(
        run_id=run_id,
        startup_idea=startup_idea,
        llm=_build_llm(),
        agents_config=agents_config,
        tasks_config=tasks_config,
        tools_map=tools_map,
        challenge_tool_factory=challenge_factory,
        publisher=publisher,
        session_factory=get_session,
    )


def _persist_r1_outputs(run_id: str, r1_outputs: dict) -> None:
    """Mirror engine.r1_outputs into the legacy Run.round1_outputs column.

    Frontend restoration code reads from this column when a user reloads
    mid-run, so we keep writing it for backward compatibility.
    """
    session = get_session()
    try:
        run = session.get(Run, run_id)
        if run is not None:
            run.round1_outputs = r1_outputs
            session.commit()
    finally:
        session.close()


def _persist_final_report(run_id: str, report: dict) -> None:
    session = get_session()
    try:
        run = session.get(Run, run_id)
        if run is not None:
            run.final_report = report
            session.commit()
    finally:
        session.close()


def run_deliberation(run_id: str, startup_idea: str, event_publisher) -> dict:
    """Execute a fresh 3-round deliberation. Returns the final report dict."""
    update_run_status(get_session(), run_id, "running")
    # Emit a single run.start event so SSE consumers can confirm the
    # deliberation is live before the first agent.start arrives.
    event_publisher({
        "type": "run.start", "run_id": run_id, "startup_idea": startup_idea,
    })
    engine = _build_engine(run_id, startup_idea, event_publisher)

    try:
        engine.run_round1()
        _persist_r1_outputs(run_id, engine.state.r1_outputs)

        engine.run_round2()
        engine.run_round3()
    except Exception as e:
        # Engine already persisted the FAILED state; surface the error to
        # the web layer so it can publish a run.failed event.
        partial = bool(engine.state.r1_outputs)
        update_run_status(get_session(), run_id, "partial" if partial else "failed")
        event_publisher({
            "type": "run.failed",
            "run_id": run_id,
            "error": repr(e),
            "partial": partial,
        })
        raise

    report = engine.state.r3_report
    _persist_final_report(run_id, report)
    update_run_status(get_session(), run_id, "complete")
    event_publisher({"type": "run.complete", "run_id": run_id, "report": report})
    return report


def resume_deliberation(run_id: str, event_publisher) -> dict:
    """Continue a deliberation from its persisted checkpoint."""
    run = get_run(get_session(), run_id)
    if run is None:
        raise ValueError(f"run {run_id} not found")

    # Build engine with the run's stored startup_idea so checkpoint load works
    engine = _build_engine(run_id, run.startup_idea, event_publisher)

    update_run_status(get_session(), run_id, "running")
    # Mirror run.start for the resume path so consumers can tell the
    # run has been picked up by a fresh worker.
    event_publisher({
        "type": "run.start", "run_id": run_id, "startup_idea": run.startup_idea,
    })

    # Capture r1_outputs pre-resume for the legacy column
    pre_r1 = dict(engine.state.r1_outputs)

    try:
        report = engine.resume()
    except Exception as e:
        partial = bool(engine.state.r1_outputs)
        update_run_status(get_session(), run_id, "partial" if partial else "failed")
        event_publisher({
            "type": "run.failed",
            "run_id": run_id,
            "error": repr(e),
            "partial": partial,
        })
        raise

    # If R1 finished during resume, persist the legacy column
    if len(engine.state.r1_outputs) > len(pre_r1):
        _persist_r1_outputs(run_id, engine.state.r1_outputs)
    _persist_final_report(run_id, report)
    update_run_status(get_session(), run_id, "complete")
    event_publisher({"type": "run.complete", "run_id": run_id, "report": report})
    return report
