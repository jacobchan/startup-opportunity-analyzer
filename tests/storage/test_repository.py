import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.storage.db import init_db
from src.storage.models import Evidence, Challenge
from src.storage.repository import (
    create_run, get_run, update_run_status,
    add_evidence, get_evidence,
    add_challenge, update_challenge_response, get_challenges_for_run,
)


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    init_db(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_create_and_get_run(db_session):
    run = create_run(db_session, startup_idea="AI Agent 平台")
    found = get_run(db_session, run.run_id)
    assert found is not None
    assert found.startup_idea == "AI Agent 平台"
    assert found.status == "queued"


def test_update_run_status(db_session):
    run = create_run(db_session, startup_idea="x")
    update_run_status(db_session, run.run_id, "running")
    found = get_run(db_session, run.run_id)
    assert found.status == "running"


def test_add_and_get_evidence(db_session):
    run = create_run(db_session, startup_idea="x")
    ev = add_evidence(
        db_session,
        run_id=run.run_id,
        source_type="search",
        query="AI Agent 市场",
        url="https://example.com",
        title="AI Agent 报告",
        content_excerpt="...",
        url_hash="abc123",
    )
    found = get_evidence(db_session, ev.evidence_id)
    assert found is not None
    assert found.url_hash == "abc123"


def test_evidence_dedup_by_url_hash(db_session):
    run = create_run(db_session, startup_idea="x")
    ev1 = add_evidence(
        db_session, run_id=run.run_id, source_type="search",
        query="q1", url="https://x.com", title="t", content_excerpt="c", url_hash="dup",
    )
    ev2 = add_evidence(
        db_session, run_id=run.run_id, source_type="search",
        query="q2", url="https://x.com", title="t", content_excerpt="c", url_hash="dup",
    )
    assert ev1.evidence_id == ev2.evidence_id


def test_list_runs_returns_most_recent_first(db_session):
    create_run(db_session, startup_idea="first")
    create_run(db_session, startup_idea="second")
    from src.storage.repository import list_runs
    runs, total = list_runs(db_session, limit=10, offset=0)
    assert len(runs) == 2
    assert runs[0].startup_idea == "second"  # newest first


def test_list_runs_respects_limit_and_offset(db_session):
    for i in range(5):
        create_run(db_session, startup_idea=f"idea {i}")
    from src.storage.repository import list_runs
    runs, total = list_runs(db_session, limit=2, offset=1)
    assert len(runs) == 2
    assert total == 5


def test_delete_run_removes_run_and_cascades(db_session):
    run = create_run(db_session, startup_idea="x")
    run_id = run.run_id
    from src.storage.repository import delete_run, add_evidence, add_challenge, get_run
    ev = add_evidence(db_session, run_id=run_id, source_type="search",
                      query="q", url=None, title=None, content_excerpt="c", url_hash="h1")
    ch = add_challenge(db_session, run_id=run_id, issuer="a", target="b", claim="c", reason="r")
    ev_id = ev.evidence_id
    ch_id = ch.challenge_id
    deleted = delete_run(db_session, run_id)
    assert deleted is True
    assert get_run(db_session, run_id) is None
    assert db_session.get(Evidence, ev_id) is None
    assert db_session.get(Challenge, ch_id) is None


def test_delete_run_returns_false_for_unknown_id(db_session):
    from src.storage.repository import delete_run
    assert delete_run(db_session, "no-such-id") is False


def test_add_challenge_and_respond(db_session):
    run = create_run(db_session, startup_idea="x")
    ch = add_challenge(
        db_session, run_id=run.run_id, issuer="market_analyst",
        target="finance_analyst", claim="LTV 假设过高", reason="...",
    )
    assert ch.verdict is None
    update_challenge_response(
        db_session, ch.challenge_id,
        response="已调整", verdict="modified",
    )
    challenges = get_challenges_for_run(db_session, run.run_id)
    assert len(challenges) == 1
    assert challenges[0].verdict == "modified"
    assert challenges[0].response == "已调整"
