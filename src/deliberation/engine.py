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
from crewai.utilities.agent_utils import AgentAction

from src.storage import (
    get_challenges_for_run,
    get_unresolved_challenges_for_run,
    mark_unresolved_as_no_response,
)

from .checkpoint import CheckpointStore
from .state import (
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
R2B_TARGETS = R2_AGENTS  # R2-B response sub-round runs for the same set
R3_AGENT = "strategy_advisor"

R2_RESPOND_TASK_KEY = "round2_respond"

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


class _SafeFormatDict(dict):
    """Mapping that leaves unknown ``{placeholders}`` intact during ``format_map``.

    CrewAI task templates often declare optional placeholders (e.g.
    ``{round2_challenges}``) that the engine only injects in later rounds.
    We want to fill in only the keys we know about and leave the rest
    untouched, so a partial format never blows up and downstream rounds
    can still see the literal placeholder for context.
    """

    def __missing__(self, key: str) -> str:  # type: ignore[override]
        return "{" + key + "}"


def _format_description(template: str, **fmt_vars: Any) -> str:
    """Format a task description template with safe missing-key handling.

    Replaces only the named placeholders that appear in ``fmt_vars``; any
    other ``{name}`` token in the template is preserved verbatim.
    """
    return template.format_map(_SafeFormatDict(**fmt_vars))


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
        step_callback: Callable[[Any], None] | None = None,
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
        # Optional CrewAI step_callback for tool.start/tool.end events
        self._step_callback = step_callback
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

    def _make_step_callback(self, agent_name: str):
        """Build a CrewAI step_callback that publishes ``tool.start`` events.

        CrewAI's step_callback fires for both ``AgentAction`` (the LLM
        has decided to call a tool) and ``AgentFinish`` (the agent has
        produced its final answer). We only translate ``AgentAction``
        into a ``tool.start`` event; the tool result is delivered to
        the LLM as part of the next step so we don't need a paired
        ``tool.end`` here.
        """
        def _cb(step):
            if isinstance(step, AgentAction):
                self._publisher({
                    "type": "tool.start",
                    "agent": agent_name,
                    "tool": getattr(step, "tool", ""),
                    "input_preview": str(getattr(step, "tool_input", ""))[:200],
                })
        return _cb

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
        # Always make startup_idea available even if the caller forgot.
        fmt_vars.setdefault("startup_idea", self._state.startup_idea)
        description = _format_description(cfg["description"], **fmt_vars)
        return Task(
            description=description,
            expected_output=cfg["expected_output"],
            agent=agent,
        )

    def _build_task_with_extras(
        self, agent: Agent, task_key: str, extras: str, **fmt_vars: Any,
    ) -> Task:
        """Build a task and append ``extras`` (e.g. inline R1 JSON) to the description.

        Centralises the ``description + extras`` pattern that R1 (risk reviewer)
        and R3 (strategy advisor) use to pass supplementary context the YAML
        template doesn't reference.
        """
        cfg = self._tasks_config[task_key]
        fmt_vars.setdefault("startup_idea", self._state.startup_idea)
        description = _format_description(cfg["description"], **fmt_vars)
        if extras:
            description = description + extras
        return Task(
            description=description,
            expected_output=cfg["expected_output"],
            agent=agent,
        )

    def _kickoff_one(self, agent_name: str, task_key: str, **fmt_vars) -> dict:
        agent = self._get_agent(agent_name)
        task = self._build_task(agent, task_key, **fmt_vars)
        crew = Crew(
            agents=[agent], tasks=[task], verbose=True,
            step_callback=self._make_step_callback(agent_name),
        )
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
                # Pair the agent.start we already published with an
                # agent.end carrying the error so SSE consumers can
                # stop their per-agent spinners and show the failure.
                self._publisher({
                    "type": "agent.end",
                    "agent": name,
                    "round": ROUND_1,
                    "output_summary": {"error": repr(e)},
                })
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
            extras = (
                "\n\n以下是前三项分析的结果，请基于这些数据完成风险评估：\n" + r1_inline
            )
            task = self._build_task_with_extras(agent, task_key, extras)
            crew = Crew(
                agents=[agent], tasks=[task], verbose=True,
                step_callback=self._make_step_callback(R1_DEPENDENT_AGENT),
            )
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
        """Run R2: issue sub-round (R2-A) followed by response sub-round (R2-B)."""
        if not from_checkpoint:
            self._state.current_round = ROUND_2
            self._save_state()
        self._publisher({
            "type": "round.transition",
            "from_round": ROUND_1, "to_round": ROUND_2,
        })

        self._run_round2_issue()
        # Reconcile bookkeeping against DB (idempotent on resume).
        self._reconcile_r2b_state_from_db()
        self._run_round2_respond()
        return list(self._state.r2_challenges)

    # ── R2-A: agents issue challenges ───────────────────

    def _run_round2_issue(self) -> None:
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
                    "response": ch.response,
                    "verdict": ch.verdict,
                })
        finally:
            session.close()
        self._state.r2_challenges = list(all_challenges)

        for agent_name in R2_AGENTS:
            if agent_name in self._state.r2_completed_agents:
                logger.info("[engine] R2-A skip %s (already done)", agent_name)
                continue
            self._publisher({
                "type": "agent.start", "agent": agent_name, "round": ROUND_2,
            })
            challenge_tool = self._challenge_tool_factory(
                run_id=self._state.run_id, agent_name=agent_name,
            )
            agent = self._get_agent(agent_name, tools_override=[challenge_tool])
            task_key = "round2_challenge"
            r1_json = json.dumps(self._state.r1_outputs, ensure_ascii=False, indent=2)
            task = self._build_task(
                agent, task_key,
                startup_idea=self._state.startup_idea,
                round1_outputs=r1_json,
            )
            crew = Crew(
                agents=[agent], tasks=[task], verbose=True,
                step_callback=self._make_step_callback(agent_name),
            )
            try:
                crew.kickoff(inputs={
                    "startup_idea": self._state.startup_idea,
                    "round1_outputs": r1_json,
                })
            except Exception as e:
                self._state.error = repr(e)
                self._state.current_round = ROUND_FAILED
                self._save_state()
                self._publisher({
                    "type": "agent.end",
                    "agent": agent_name, "round": ROUND_2,
                    "output_summary": {"error": repr(e)},
                })
                raise

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
                            "response": ch.response,
                            "verdict": ch.verdict,
                        }
                        all_challenges.append(d)
                        self._publisher({"type": "challenge.issued", **{
                            "challenge_id": d["challenge_id"],
                            "issuer": d["issuer"],
                            "target": d["target"],
                            "claim": d["claim"],
                            "reason": d["reason"],
                        }})
            finally:
                session.close()

            self._state.r2_challenges = list(all_challenges)
            self._state.r2_completed_agents.append(agent_name)
            self._save_state()
            self._publisher({
                "type": "agent.end", "agent": agent_name, "round": ROUND_2,
            })

    # ── R2-B: targeted agents respond to challenges ─────

    def _reconcile_r2b_state_from_db(self) -> None:
        """No-op for now: we keep ``r2b_completed_targets`` and
        ``r2_resolved_challenge_ids`` as best-effort in-memory hints, while
        the database (Challenge.response IS NULL) is the source of truth for
        "what still needs a response". See ``_run_round2_respond``.
        """
        return

    def _run_round2_respond(self) -> None:
        """For each target agent that still has unresolved challenges, run
        a kickoff with the respond-capable tool and the round2_respond task.
        After the kickoff, mark any challenge the LLM didn't respond to as
        no_response so R3 always sees a complete disposition.
        """
        # Collect unresolved challenges from the DB
        session = self._session_factory()
        try:
            all_unresolved = get_unresolved_challenges_for_run(
                session=session, run_id=self._state.run_id,
            )
        finally:
            session.close()

        # Group by target, fixed dict order for deterministic resume
        by_target: dict[str, list] = {t: [] for t in R2B_TARGETS}
        for ch in all_unresolved:
            if ch.target in by_target:
                by_target[ch.target].append(ch)
            else:
                logger.warning("[engine] unresolved challenge targets unknown agent %s", ch.target)

        for target in R2B_TARGETS:
            open_for_target = by_target[target]
            if not open_for_target:
                # Nothing to respond to for this target
                continue
            if target in self._state.r2b_completed_targets:
                logger.info("[engine] R2-B skip %s (already done)", target)
                continue

            # Snapshot the open challenges as a serializable list
            open_payload = [
                {
                    "challenge_id": ch.challenge_id,
                    "issuer": ch.issuer,
                    "claim": ch.claim,
                    "reason": ch.reason,
                }
                for ch in open_for_target
            ]
            self._publisher({
                "type": "agent.start", "agent": target, "round": ROUND_2,
            })

            # Build a fresh respond-only tool; max_challenges=0 disables issuing.
            challenge_tool = self._challenge_tool_factory(
                run_id=self._state.run_id, agent_name=target, max_challenges=0,
            )
            agent = self._get_agent(target, tools_override=[challenge_tool])
            extras = (
                "\n\n以下是别人对你的、尚未回应的挑战列表（JSON 格式）：\n"
                + json.dumps(open_payload, ensure_ascii=False, indent=2)
            )
            task = self._build_task_with_extras(
                agent, R2_RESPOND_TASK_KEY, extras,
                open_challenges_for_me=json.dumps(
                    open_payload, ensure_ascii=False, indent=2,
                ),
            )
            crew = Crew(
                agents=[agent], tasks=[task], verbose=True,
                step_callback=self._make_step_callback(target),
            )
            try:
                crew.kickoff(inputs={
                    "startup_idea": self._state.startup_idea,
                    "open_challenges_for_me": json.dumps(
                        open_payload, ensure_ascii=False, indent=2,
                    ),
                })
            except Exception as e:
                self._state.error = repr(e)
                self._state.current_round = ROUND_FAILED
                self._save_state()
                self._publisher({
                    "type": "agent.end",
                    "agent": target, "round": ROUND_2,
                    "output_summary": {"error": repr(e)},
                })
                raise

            # Safety net: any challenge still response IS NULL gets no_response
            session = self._session_factory()
            try:
                mark_unresolved_as_no_response(
                    session=session, run_id=self._state.run_id, target=target,
                )
            finally:
                session.close()

            # Emit challenge.responded for every challenge whose response
            # was set (whether by the LLM or the no_response safety net)
            session = self._session_factory()
            try:
                for ch in get_challenges_for_run(session, self._state.run_id):
                    if ch.target == target and ch.response is not None:
                        self._publisher({
                            "type": "challenge.responded",
                            "challenge_id": ch.challenge_id,
                            "target": ch.target,
                            "response": ch.response,
                            "verdict": ch.verdict,
                        })
                        if ch.challenge_id not in self._state.r2_resolved_challenge_ids:
                            self._state.r2_resolved_challenge_ids.append(
                                ch.challenge_id,
                            )
            finally:
                session.close()

            self._state.r2b_completed_targets.append(target)
            self._save_state()
            self._publisher({
                "type": "agent.end", "agent": target, "round": ROUND_2,
            })

    # ── Round 3 ────────────────────────────────────────


    def _build_challenge_disposition(self) -> dict:
        """Group every R2 challenge by verdict for the R3 prompt.

        The DB is the source of truth — the in-memory ``state.r2_challenges``
        may be stale on resume. Each bucket holds ``{challenge_id, claim,
        response, issuer}`` dicts. Buckets with no entries are still emitted
        as empty lists so the LLM always sees the full four-key shape.
        """
        session = self._session_factory()
        try:
            rows = get_challenges_for_run(session, self._state.run_id)
        finally:
            session.close()
        buckets: dict[str, list[dict]] = {
            "accepted": [], "rejected": [], "modified": [], "no_response": [],
        }
        for ch in rows:
            verdict = (ch.verdict or "no_response").strip()
            bucket = buckets.get(verdict)
            if bucket is None:
                # Unknown verdict — keep going but log
                logger.warning("[engine] unknown verdict %r on challenge %s", verdict, ch.challenge_id)
                continue
            bucket.append({
                "challenge_id": ch.challenge_id,
                "claim": ch.claim,
                "response": ch.response or "",
                "issuer": ch.issuer,
            })
        return buckets

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

        # Build a verdict-grouped disposition block so the strategy_advisor
        # can cite accepted/modified challenges in key_risks.
        disposition = self._build_challenge_disposition()
        disposition_json = json.dumps(disposition, ensure_ascii=False, indent=2)

        agent = self._get_agent(R3_AGENT)
        task_key = _TASK_KEY[R3_AGENT]
        extras = (
            f"\n\n以下是四个分析 agent 的详细输出：\n{r1_json}"
            + f"\n\n以下是交叉挑战的完整记录（含回应与裁决）：\n{challenges_json}"
            + f"\n\n以下是按裁决分桶的挑战处置摘要 (challenge_disposition)：\n{disposition_json}"
        )
        task = self._build_task_with_extras(
            agent, task_key, extras,
            round1_outputs=r1_json,
            round2_challenges=challenges_json,
            challenge_disposition=disposition_json,
        )
        crew = Crew(
            agents=[agent], tasks=[task], verbose=True,
            step_callback=self._make_step_callback(R3_AGENT),
        )
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
