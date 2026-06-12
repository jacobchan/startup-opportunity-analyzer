from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import select

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


def get_challenges_for_run(session: Session, run_id: str) -> list[Challenge]:
    stmt = select(Challenge).where(Challenge.run_id == run_id).order_by(Challenge.issued_at)
    return list(session.execute(stmt).scalars())


def _set_final_report_for_test(run_id: str, report: dict) -> None:
    """Test helper: directly write final_report to a run."""
    session = get_session()
    run = session.get(Run, run_id)
    if run is None:
        return
    run.final_report = report
    session.commit()
