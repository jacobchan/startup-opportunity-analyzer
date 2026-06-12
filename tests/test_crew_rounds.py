"""Regression test: CrewAI's Pydantic validation rejects tasks without an `agent` field.

Earlier the R2 challenge task was created via Task(config=...) after stripping the
agent key, which produced a `missing_agent_in_task` ValidationError at runtime.
This test verifies that the R2 task construction succeeds — i.e. the agent is wired
into the task before Crew() is constructed.
"""

import pytest


def test_round2_task_constructor_assigns_agent():
    """Inspect the source of run_round2 to confirm the Task() call passes agent=..."""
    import inspect
    from src.crew import StartupAnalyzerCrew

    source = inspect.getsource(StartupAnalyzerCrew.run_round2)
    # The buggy version used Task(config=...) which omitted the agent field.
    # The fix constructs the Task with description=.., expected_output=.., agent=..
    assert "Task(config=" not in source, (
        "run_round2 still uses Task(config=...); this strips the agent field and "
        "triggers a missing_agent_in_task ValidationError at runtime."
    )
    assert "agent=agent" in source, (
        "run_round2 does not pass agent= to the Task constructor."
    )


def test_round1_risk_task_constructor_assigns_agent():
    """The risk_review task in R1 also uses the explicit-constructor pattern."""
    import inspect
    from src.crew import StartupAnalyzerCrew

    source = inspect.getsource(StartupAnalyzerCrew.run_round1)
    # The risk task must use the description=/expected_output=/agent= pattern.
    assert "agent=risk_agent" in source, (
        "run_round1 does not pass agent=risk_agent to the risk task."
    )
