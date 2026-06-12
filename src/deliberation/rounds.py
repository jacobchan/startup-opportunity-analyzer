from dataclasses import dataclass, field


ROUND_ORDER = ["round1", "round2", "round3"]


@dataclass
class RoundTransition:
    from_round: str | None
    to_round: str


class RoundOrchestrator:
    def __init__(self, run_id: str, agents: dict, tasks: dict, event_publisher):
        self.run_id = run_id
        self.agents = agents
        self.tasks = tasks
        self._publisher = event_publisher
        self._current_round: str | None = None
        self.r1_outputs: dict = {}
        self.challenge_ids: list[str] = []

    @property
    def current_round(self) -> str | None:
        return self._current_round

    def transition_to(self, to_round: str) -> None:
        if to_round not in ROUND_ORDER:
            raise ValueError(f"unknown round: {to_round}")
        if self._current_round is None:
            if to_round != ROUND_ORDER[0]:
                raise ValueError(
                    f"invalid transition: None -> {to_round} "
                    f"(must start at {ROUND_ORDER[0]})"
                )
        else:
            current_idx = ROUND_ORDER.index(self._current_round)
            target_idx = ROUND_ORDER.index(to_round)
            if target_idx != current_idx + 1:
                raise ValueError(
                    f"invalid transition: {self._current_round} -> {to_round} "
                    f"(must follow order: {ROUND_ORDER})"
                )
        self._publisher({
            "type": "round.transition",
            "from_round": self._current_round,
            "to_round": to_round,
        })
        self._current_round = to_round

    def record_r1_output(self, agent_name: str, output: dict) -> None:
        self.r1_outputs[agent_name] = output

    def record_challenge(self, challenge: dict) -> None:
        self.challenge_ids.append(challenge["challenge_id"])
