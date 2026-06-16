"""Deliberation engine state - serializable, checkpointable."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field

# Round identifiers used in events and persistence
ROUND_NONE = "none"
ROUND_1 = "round1"
ROUND_2 = "round2"
ROUND_3 = "round3"
ROUND_COMPLETE = "complete"
ROUND_FAILED = "failed"

ALL_ROUNDS = (ROUND_1, ROUND_2, ROUND_3)
TERMINAL_ROUNDS = (ROUND_COMPLETE, ROUND_FAILED)


RoundStatus = Literal["none", "round1", "round2", "round3", "complete", "failed"]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class EngineState(BaseModel):
    """Serializable state for the deliberation engine.

    Stored as JSON in ``Run.deliberation_state``. Every write to the
    in-memory state must be followed by a checkpoint save so a crash
    can resume from the latest persisted snapshot.
    """

    run_id: str
    startup_idea: str
    current_round: RoundStatus = ROUND_NONE
    r1_outputs: dict[str, dict] = Field(default_factory=dict)
    r1_completed_agents: list[str] = Field(default_factory=list)
    r2_challenges: list[dict] = Field(default_factory=list)
    r2_completed_agents: list[str] = Field(default_factory=list)
    r3_report: dict | None = None
    error: str | None = None
    updated_at: str = Field(default_factory=_now_iso)

    def is_resumable(self) -> bool:
        return self.current_round in (ROUND_1, ROUND_2, ROUND_3)

    def is_terminal(self) -> bool:
        return self.current_round in TERMINAL_ROUNDS
