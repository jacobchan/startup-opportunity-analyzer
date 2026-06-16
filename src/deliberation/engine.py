"""Deliberation engine: stateful 3-round orchestrator with resume support.

Replaces the per-round cold-start Crew pattern in ``src/crew.py``. The
engine owns:

- A single ``LLM`` instance shared across all rounds
- A cached map of agent name -> Agent (so we don't re-instantiate per
  kickoff). R2 passes a challenge-only tool override, which builds a
  fresh Agent and never pollutes the cache.
- A serializable ``EngineState`` checkpointed to ``Run.deliberation_state``
  after every agent completes, so a crash mid-deliberation can resume
  from the last completed agent.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Callable

from crewai import Agent, Crew, LLM, Task
from crewai.tools import BaseTool

from src.storage import get_challenges_for_run

from .checkpoint import CheckpointStore
from .state import (
    ALL_ROUNDS,
    EngineState,
    ROUND_1,
    ROUND_2,
    ROUND_3,
    ROUND_COMPLETE,
    ROUND_FAILED,
    ROUND_NONE,
)

logger = logging.getLogger(__name__)


# Agent name <-> tasks.yaml key mapping
R1_INDEPENDENT_AGENTS = ("market_analyst", "competitor_researcher", "finance_analyst")
R1_DEPENDENT_AGENT = "risk_reviewer"
R2_AGENTS = ("market_analyst", "competitor_researcher", "finance_analyst")
R3_AGENT = "strategy_advisor"

# tasks.yaml key for each agent
_TASK_KEY = {
    "market_analyst": "market_analysis",
    "competitor_researcher": "competitor_analysis",
    "finance_analyst": "finance_analysis",
    "risk_reviewer": "risk_review",
    "strategy_advisor": "strategy_report",
}


def _parse_json_output(raw: Any) -> dict:
    """Mirror src.crew._parse_json but stay self-contained for the engine."""
    text = str(raw).strip()
    if text.startswith("```"):
        lines = text.split("\n")
        start = 1
        end = len(lines)
        for i in range(len(lines) - 1, -1, -1):
            if lines[i].strip() == "```":
                end = i
                break
        text = "\n".join(lines[start:end]).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"raw_output": str(raw), "parse_error": True}


class DeliberationEngine:
    """3-round deliberation with checkpoint + resume."""

    def __init__(
        self,
        run_id: str,
        startup_idea: str,
        llm: LLM,
        agents_config: dict,
        tasks_config: dict,
        tools_map: dict[str, list[BaseTool]],
        challenge_tool_factory: Callable[..., BaseTool],
        publisher: Callable[[dict], None],
        session_factory: Callable[[], Any],
        state: EngineState | None = None,
        agent_factory: Callable[[str, list[BaseTool] | None], Agent] | None = None,
    ):
        self._llm = llm
        self._agents_config = agents_config
        self._tasks_config = tasks_config
        self._tools_map = tools_map
        self._challenge_tool_factory = challenge_tool_factory
        self._publisher = publisher
        self._checkpoint = CheckpointStore(session_factory)
        self._session_factory = session_factory
        self._agent_cache: dict[str, Agent] = {}
        # Optional factory override (used by tests to inject mocks)
        self._agent_factory_override = agent_factory
        # Reuse provided state (for resume) or load from DB, else init fresh
        if state is not None:
            self._state = state
        else:
            loaded = self._checkpoint.load(run_id)
            if loaded is not None:
                self._state = loaded
            else:
                self._state = self._checkpoint.init_fresh(run_id, startup_idea)

    # ── Agent / Task factories ─────────────────────────

    def _get_agent(self, name: str, tools_override: list[BaseTool] | None = None) -> Agent:
        if self._agent_factory_override is not None:
            return self._agent_factory_override(name, tools_override)
        if tools_override is None:
            if name in self._agent_cache:
                return self._agent_cache[name]
            tools = self._tools_map.get(name, [])
            agent = Agent(
                config=self._agents_config[name],
                tools=tools,
                llm=self._llm,
                verbose=True,
            )
            self._agent_cache[name] = agent
            return agent
        # Override path - always build a fresh Agent so the cache stays clean
        return Agent(
            config=self._agents_config[name],
            tools=tools_override,
            llm=self._llm,
            verbose=True,
        )

    def _build_task(self, agent: Agent, task_key: str, **fmt_vars) -> Task:
        cfg = self._tasks_config[task_key]
        description = cfg["description"]
        # The templates use {startup_idea} and sometimes {round1_outputs} /
        # {round2_challenges} / {round1_outputs_inline} placeholders.
        # We do safe formatting: ignore missing keys so callers can pass
        # only what each task needs.
        try:
            description = description.format(**fmt_vars)
        except KeyError:
            # Fallback: inject the few we know about
            description = description.format(startup_idea=self._state.startup_idea)
        return Task(
            description=description,
            expected_output=cfg["expected_output"],
            agent=agent,
        )

    def _kickoff_one(self, agent_name: str, task_key: str, **fmt_vars) -> dict:
        agent = self._get_agent(agent_name)
        task = self._build_task(agent, task_key, **fmt_vars)
        crew = Crew(agents=[agent], tasks=[task], verbose=True)
        inputs = {"startup_idea": self._state.startup_idea}
        inputs.update(fmt_vars)
        result = crew.kickoff(inputs=inputs)
        return _parse_json_output(result.raw)


    # ── Round 1 ────────────────────────────────────────

    def run_round1(self, from_checkpoint: bool = False) -> dict:
        if not from_checkpoint:
            self._state.current_round = ROUND_1
            self._save_state()
        self._publisher({
            "type": "round.transition",
            "from_round": None if not from_checkpoint else None,
            "to_round": ROUND_1,
        })

        for name in R1_INDEPENDENT_AGENTS:
            if name in self._state.r1_completed_agents:
                logger.info("[engine] R1 skip %s (already done)", name)
                continue
            self._publisher({"type": "agent.start", "agent": name, "round": ROUND_1})
            try:
                output = self._kickoff_one(name, _TASK_KEY[name])
            except Exception as e:  # surface to caller; let resume retry
                self._state.error = repr(e)
                self._state.current_round = ROUND_FAILED
                self._save_state()
                raise
            self._state.r1_outputs[name] = output
            self._state.r1_completed_agents.append(name)
            self._save_state()
            self._publisher({
                "type": "agent.end", "agent": name, "round": ROUND_1,
                "output_summary": output,
            })

        if R1_DEPENDENT_AGENT not in self._state.r1_completed_agents:
            self._publisher({
                "type": "agent.start", "agent": R1_DEPENDENT_AGENT, "round": ROUND_1,
            })
            r1_inline = json.dumps(
                {k: self._state.r1_outputs[k] for k in R1_INDEPENDENT_AGENTS},
                ensure_ascii=False, indent=2,
            )
            # tasks.yaml for risk_review uses no {round1_outputs} placeholder,
            # so we keep the same behavior as the original code: append the
            # JSON into the description via a wrapper.
            task_key = _TASK_KEY[R1_DEPENDENT_AGENT]
            agent = self._get_agent(R1_DEPENDENT_AGENT)
            cfg = self._tasks_config[task_key]
            wrapped_desc = cfg["description"] + (
                "\n\n以下是前三项分析的结果，请基于这些数据完成风险评估：\n" + r1_inline
            )
            task = Task(
                description=wrapped_desc,
                expected_output=cfg["expected_output"],
                agent=agent,
            )
            crew = Crew(agents=[agent], tasks=[task], verbose=True)
            result = crew.kickoff(inputs={"startup_idea": self._state.startup_idea})
            output = _parse_json_output(result.raw)
            self._state.r1_outputs[R1_DEPENDENT_AGENT] = output
            self._state.r1_completed_agents.append(R1_DEPENDENT_AGENT)
            self._save_state()
            self._publisher({
                "type": "agent.end", "agent": R1_DEPENDENT_AGENT, "round": ROUND_1,
                "output_summary": output,
            })

        return dict(self._state.r1_outputs)

    # ── Round 2 ────────────────────────────────────────

    def run_round2(self, from_checkpoint: bool = False) -> list[dict]:
        if not from_checkpoint:
            self._state.current_round = ROUND_2
            self._save_state()
        self._publisher({
            "type": "round.transition",
            "from_round": ROUND_1, "to_round": ROUND_2,
        })

        all_challenges: list[dict] = []
        seen_ids: set[str] = set()
        # Re-seed from already-persisted challenges (covers resume case)
        session = self._session_factory()
        try:
            for ch in get_challenges_for_run(session, self._state.run_id):
                seen_ids.add(ch.challenge_id)
                all_challenges.append({
                    "challenge_id": ch.challenge_id,
                    "issuer": ch.issuer,
                    "target": ch.target,
                    "claim": ch.claim,
                    "reason": ch.reason,
                })
        finally:
            session.close()
        self._state.r2_challenges = list(all_challenges)

        for agent_name in R2_AGENTS:
            if agent_name in self._state.r2_completed_agents:
                logger.info("[engine] R2 skip %s (already done)", agent_name)
                continue
            self._publisher({
                "type": "agent.start", "agent": agent_name, "round": ROUND_2,
            })
            challenge_tool = self._challenge_tool_factory(
                run_id=self._state.run_id, agent_name=agent_name,
            )
            agent = self._get_agent(agent_name, tools_override=[challenge_tool])
            task_key = "round2_challenge"
            cfg = self._tasks_config[task_key]
            r1_json = json.dumps(self._state.r1_outputs, ensure_ascii=False, indent=2)
            try:
                description = cfg["description"].format(
                    startup_idea=self._state.startup_idea,
                    round1_outputs=r1_json,
                )
            except KeyError:
                description = cfg["description"]
            task = Task(
                description=description,
                expected_output=cfg["expected_output"],
                agent=agent,
            )
            crew = Crew(agents=[agent], tasks=[task], verbose=True)
            crew.kickoff(inputs={
                "startup_idea": self._state.startup_idea,
                "round1_outputs": r1_json,
            })

            # Collect any challenges this agent newly issued
            session = self._session_factory()
            try:
                for ch in get_challenges_for_run(session, self._state.run_id):
                    if ch.issuer == agent_name and ch.challenge_id not in seen_ids:
                        seen_ids.add(ch.challenge_id)
                        d = {
                            "challenge_id": ch.challenge_id,
                            "issuer": ch.issuer,
                            "target": ch.target,
                            "claim": ch.claim,
                            "reason": ch.reason,
                        }
                        all_challenges.append(d)
                        self._publisher({"type": "challenge.issued", **d})
            finally:
                session.close()

            self._state.r2_challenges = list(all_challenges)
            self._state.r2_completed_agents.append(agent_name)
            self._save_state()
            self._publisher({
                "type": "agent.end", "agent": agent_name, "round": ROUND_2,
            })

        return list(all_challenges)

    # ── Round 3 ────────────────────────────────────────

    def run_round3(self, from_checkpoint: bool = False) -> dict:
        if not from_checkpoint:
            self._state.current_round = ROUND_3
            self._save_state()
        self._publisher({
            "type": "round.transition",
            "from_round": ROUND_2, "to_round": ROUND_3,
        })

        if self._state.r3_report is not None:
            return dict(self._state.r3_report)

        self._publisher({"type": "agent.start", "agent": R3_AGENT, "round": ROUND_3})
        r1_json = json.dumps(self._state.r1_outputs, ensure_ascii=False, indent=2)
        challenges_json = json.dumps(self._state.r2_challenges, ensure_ascii=False, indent=2)

        agent = self._get_agent(R3_AGENT)
        cfg = self._tasks_config[_TASK_KEY[R3_AGENT]]
        try:
            description = cfg["description"].format(
                startup_idea=self._state.startup_idea,
                round1_outputs=r1_json,
                round2_challenges=challenges_json,
            )
        except KeyError:
            description = cfg["description"]
        # Original code appends the inline blocks to the description
        description = (
            description
            + f"\n\n以下是四个分析 agent 的详细输出：\n{r1_json}"
            + f"\n\n以下是交叉挑战记录：\n{challenges_json}"
        )
        task = Task(
            description=description,
            expected_output=cfg["expected_output"],
            agent=agent,
        )
        crew = Crew(agents=[agent], tasks=[task], verbose=True)
        result = crew.kickoff(inputs={"startup_idea": self._state.startup_idea})
        output = _parse_json_output(result.raw)
        self._state.r3_report = output
        self._state.current_round = ROUND_COMPLETE
        self._save_state()
        self._publisher({
            "type": "agent.end", "agent": R3_AGENT, "round": ROUND_3,
            "output_summary": output,
        })
        return output

    # ── Top-level entry points ─────────────────────────

    def run_all(self) -> dict:
        try:
            self.run_round1()
            self.run_round2()
            return self.run_round3()
        except Exception as e:
            self._state.error = repr(e)
            if self._state.current_round not in (ROUND_COMPLETE, ROUND_FAILED):
                self._state.current_round = ROUND_FAILED
            self._save_state()
            raise

    def resume(self) -> dict:
        """Continue from the current persisted state."""
        cur = self._state.current_round
        if cur == ROUND_COMPLETE and self._state.r3_report is not None:
            return dict(self._state.r3_report)
        if cur == ROUND_FAILED:
            raise RuntimeError(f"cannot resume failed run: {self._state.error}")
        if cur == ROUND_1 or cur == ROUND_NONE:
            self.run_round1(from_checkpoint=True)
            self.run_round2(from_checkpoint=True)
            return self.run_round3(from_checkpoint=True)
        if cur == ROUND_2:
            self.run_round2(from_checkpoint=True)
            return self.run_round3(from_checkpoint=True)
        if cur == ROUND_3:
            return self.run_round3(from_checkpoint=True)
        raise RuntimeError(f"unknown round state: {cur}")

    # ── Helpers ────────────────────────────────────────

    def _save_state(self) -> None:
        from datetime import datetime, timezone
        self._state.updated_at = datetime.now(timezone.utc).isoformat()
        self._checkpoint.save(self._state)

    @property
    def state(self) -> EngineState:
        return self._state
