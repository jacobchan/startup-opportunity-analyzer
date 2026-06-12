import pytest

from src.deliberation.protocol import ChallengeDraft, Verdict


def test_challenge_draft_required_fields():
    draft = ChallengeDraft(
        issuer="market_analyst",
        target="finance_analyst",
        claim="LTV 假设过高",
        reason="同行业基准是 X",
    )
    assert draft.issuer == "market_analyst"
    assert draft.target == "finance_analyst"


def test_verdict_enum_members():
    assert Verdict.ACCEPTED.value == "accepted"
    assert Verdict.REJECTED.value == "rejected"
    assert Verdict.MODIFIED.value == "modified"


def test_challenge_draft_rejects_empty_claim():
    with pytest.raises(ValueError):
        ChallengeDraft(issuer="a", target="b", claim="", reason="d")


def test_challenge_draft_rejects_self_challenge():
    with pytest.raises(ValueError):
        ChallengeDraft(issuer="a", target="a", claim="c", reason="d")
