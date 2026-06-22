from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from sqlalchemy import delete as sql_delete

from src.storage.db import get_session
from src.storage.models import Run, Evidence, Challenge


def create_run(session: Session, startup_idea: str) -> Run:
    run = Run(startup_idea=startup_idea)
    session.add(run)
    session.commit()
    session.refresh(run)
    return run


def get_run(session: Session, run_id: str) -> Run | None:
    return session.get(Run, run_id)


def update_run_status(session: Session, run_id: str, status: str) -> None:
    run = session.get(Run, run_id)
    if run is None:
        return
    run.status = status
    if status in ("complete", "failed", "partial"):
        run.completed_at = datetime.now(timezone.utc)
    session.commit()


def save_deliberation_state(session: Session, run_id: str, state: dict) -> Run | None:
    """Persist the deliberation engine state for resumable runs."""
    run = session.get(Run, run_id)
    if run is None:
        return None
    run.deliberation_state = state
    session.commit()
    session.refresh(run)
    return run


def load_deliberation_state(session: Session, run_id: str) -> dict | None:
    """Load the deliberation engine state for a run, or None if not started."""
    run = session.get(Run, run_id)
    if run is None:
        return None
    return run.deliberation_state


def _url_hash_to_existing(session: Session, url_hash: str) -> Evidence | None:
    stmt = select(Evidence).where(Evidence.url_hash == url_hash).limit(1)
    return session.execute(stmt).scalar_one_or_none()


def add_evidence(
    session: Session, run_id: str, source_type: str, query: str,
    url: str | None, title: str | None, content_excerpt: str, url_hash: str,
) -> Evidence:
    existing = _url_hash_to_existing(session, url_hash)
    if existing is not None:
        return existing
    ev = Evidence(
        run_id=run_id, source_type=source_type, query=query,
        url=url, title=title, content_excerpt=content_excerpt, url_hash=url_hash,
    )
    session.add(ev)
    session.commit()
    session.refresh(ev)
    return ev


def get_evidence(session: Session, evidence_id: str) -> Evidence | None:
    return session.get(Evidence, evidence_id)


def add_challenge(
    session: Session, run_id: str, issuer: str, target: str,
    claim: str, reason: str,
) -> Challenge:
    ch = Challenge(
        run_id=run_id, issuer=issuer, target=target,
        claim=claim, reason=reason,
    )
    session.add(ch)
    session.commit()
    session.refresh(ch)
    return ch


def update_challenge_response(
    session: Session, challenge_id: str, response: str, verdict: str,
) -> Challenge | None:
    ch = session.get(Challenge, challenge_id)
    if ch is None:
        return None
    ch.response = response
    ch.verdict = verdict
    ch.resolved_at = datetime.now(timezone.utc)
    session.commit()
    session.refresh(ch)
    return ch


def get_challenge(session: Session, challenge_id: str) -> Challenge | None:
    """Look up a single challenge by id."""
    return session.get(Challenge, challenge_id)


def get_challenges_for_run(session: Session, run_id: str) -> list[Challenge]:
    """All challenges for a run, ordered by issued_at."""
    stmt = select(Challenge).where(Challenge.run_id == run_id).order_by(Challenge.issued_at)
    return list(session.execute(stmt).scalars())


def get_unresolved_challenges_for_run(
    session: Session, run_id: str, target: str | None = None,
) -> list[Challenge]:
    """Return challenges with ``response IS NULL``.

    If ``target`` is given, restrict to challenges targeting that agent.
    Used by R2-B to decide which agents still have open work.
    """
    stmt = (
        select(Challenge)
        .where(Challenge.run_id == run_id, Challenge.response.is_(None))
        .order_by(Challenge.issued_at)
    )
    if target is not None:
        stmt = stmt.where(Challenge.target == target)
    return list(session.execute(stmt).scalars())


def mark_unresolved_as_no_response(
    session: Session, run_id: str, target: str,
) -> int:
    """Fill ``verdict='no_response' / resolved_at=now`` for every challenge
    in this run targeting ``target`` that still has ``response IS NULL``.

    Returns the number of rows updated. Used as the R2-B safety net: if the
    LLM finished its kickoff without calling ``respond`` for some challenges,
    we still mark them as no_response so R3 always sees a complete disposition.
    """
    rows = get_unresolved_challenges_for_run(
        session=session, run_id=run_id, target=target,
    )
    now = datetime.now(timezone.utc)
    for ch in rows:
        ch.verdict = "no_response"
        ch.resolved_at = now
    if rows:
        session.commit()
    return len(rows)


def count_unresolved_for_run(session: Session, run_id: str) -> int:
    """Return the number of challenges in this run that still have ``response IS NULL``."""
    stmt = (
        select(func.count(Challenge.challenge_id))
        .where(Challenge.run_id == run_id, Challenge.response.is_(None))
    )
    return int(session.execute(stmt).scalar_one())


def list_runs(session: Session, limit: int = 10, offset: int = 0) -> tuple[list[Run], int]:
    """Return (runs ordered by created_at DESC, total count)."""
    total = session.execute(select(func.count(Run.run_id))).scalar_one()
    stmt = select(Run).order_by(Run.created_at.desc()).limit(limit).offset(offset)
    runs = list(session.execute(stmt).scalars())
    return runs, total


def delete_run(session: Session, run_id: str) -> bool:
    """Hard-delete a run and its associated evidence + challenges. Returns True if deleted."""
    run = session.get(Run, run_id)
    if run is None:
        return False
    session.execute(sql_delete(Evidence).where(Evidence.run_id == run_id))
    session.execute(sql_delete(Challenge).where(Challenge.run_id == run_id))
    session.delete(run)
    session.commit()
    return True


def _set_final_report_for_test(run_id: str, report: dict) -> None:
    """Test helper: directly write final_report to a run."""
    session = get_session()
    run = session.get(Run, run_id)
    if run is None:
        return
    run.final_report = report
    session.commit()
