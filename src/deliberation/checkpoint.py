"""SQLite-backed checkpoint store for EngineState."""

from __future__ import annotations

from sqlalchemy.orm import Session

from src.storage import load_deliberation_state, save_deliberation_state

from .state import EngineState, ROUND_NONE


class CheckpointStore:
    """Persists EngineState to Run.deliberation_state.

    Uses the existing Run row as the storage location - one JSON column
    per run, no extra table. Reasonable for state sizes < 500KB; if a
    run ever grows beyond that we'll move it to a dedicated table.
    """

    def __init__(self, session_factory):
        self._session_factory = session_factory

    def save(self, state: EngineState) -> None:
        session: Session = self._session_factory()
        try:
            payload = state.model_dump(mode="json")
            save_deliberation_state(session, state.run_id, payload)
        finally:
            session.close()

    def load(self, run_id: str) -> EngineState | None:
        session: Session = self._session_factory()
        try:
            data = load_deliberation_state(session, run_id)
        finally:
            session.close()
        if data is None:
            return None
        return EngineState.model_validate(data)

    def init_fresh(self, run_id: str, startup_idea: str) -> EngineState:
        """Create a new EngineState and persist it. Used for new runs."""
        state = EngineState(run_id=run_id, startup_idea=startup_idea)
        self.save(state)
        return state
