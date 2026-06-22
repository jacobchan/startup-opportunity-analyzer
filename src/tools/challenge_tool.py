"""Challenge tool: issue, respond, and list open challenges.

One tool instance, three actions:

- ``challenge(target, claim, reason)`` — issue a new challenge. Counted against
  the per-agent ``max_challenges`` quota.
- ``respond(challenge_id, response, verdict)`` — record a response to a
  challenge targeting this issuer. Not counted.
- ``list_open_challenges(target)`` — return challenges where ``target == self.issuer``
  and ``response IS NULL``. Not counted.

Only ``challenge`` enforces ``max_challenges``; setting ``max_challenges=0``
disables the issue action while still letting the LLM respond and list.
"""

from __future__ import annotations

from typing import Any

from crewai.tools import BaseTool

from src.storage import (
    add_challenge,
    get_session,
    get_unresolved_challenges_for_run,
    update_challenge_response,
)


VALID_VERDICTS = ("accepted", "rejected", "modified", "no_response")


class ChallengeTool(BaseTool):
    name: str = "challenge"
    description: str = (
        "对其他 agent 的结论提出挑战，或回应别人对你的挑战。\n"
        "支持三种动作：\n"
        "1) action='challenge'：发起挑战。输入: target, claim, reason。\n"
        "2) action='respond'：回应挑战。输入: challenge_id, response, verdict "
        "(verdict ∈ accepted|rejected|modified)。\n"
        "3) action='list_open'：列出别人对你的、尚未回应的挑战。"
        "输入: target (传 self 的 agent 名)。\n"
        "发起挑战会消耗本 agent 的 quota（默认 3 次），回应和查询不消耗。"
    )

    run_id: str
    issuer: str
    _count: int = 0
    max_challenges: int = 3

    def _run(
        self,
        action: str,
        target: str | None = None,
        claim: str | None = None,
        reason: str | None = None,
        challenge_id: str | None = None,
        response: str | None = None,
        verdict: str | None = None,
    ) -> Any:
        action = (action or "").strip().lower()
        if action == "challenge":
            return self._issue(target or "", claim or "", reason or "")
        if action == "respond":
            return self._respond(challenge_id or "", response or "", verdict or "")
        if action == "list_open":
            return self._list_open(target or self.issuer)
        raise ValueError(
            f"unknown action: {action!r}. Use 'challenge', 'respond', or 'list_open'."
        )

    # ── actions ────────────────────────────────────────

    def _issue(self, target: str, claim: str, reason: str) -> str:
        if self.max_challenges <= 0:
            raise RuntimeError(
                f"challenge issuance is disabled for {self.issuer} in this sub-round"
            )
        if not claim.strip():
            raise ValueError("claim cannot be empty")
        if target == self.issuer:
            raise ValueError("cannot challenge yourself")
        if self._count >= self.max_challenges:
            raise RuntimeError(
                f"max challenges ({self.max_challenges}) reached for {self.issuer}"
            )
        session = get_session()
        try:
            ch = add_challenge(
                session=session,
                run_id=self.run_id,
                issuer=self.issuer,
                target=target,
                claim=claim,
                reason=reason,
            )
        finally:
            session.close()
        self._count += 1
        return f"挑战已发出 challenge_id={ch.challenge_id}，等待 {target} 回应"

    def _respond(self, challenge_id: str, response: str, verdict: str) -> str:
        if not challenge_id.strip():
            raise ValueError("challenge_id cannot be empty")
        if not response.strip():
            raise ValueError("response cannot be empty")
        if verdict not in ("accepted", "rejected", "modified"):
            raise ValueError(
                f"verdict must be one of accepted|rejected|modified, got {verdict!r}"
            )
        session = get_session()
        try:
            ch = update_challenge_response(
                session=session,
                challenge_id=challenge_id,
                response=response,
                verdict=verdict,
            )
        finally:
            session.close()
        if ch is None:
            raise ValueError(f"challenge {challenge_id} not found")
        if ch.target != self.issuer:
            raise ValueError(
                f"challenge {challenge_id} targets {ch.target!r}, not this issuer {self.issuer!r}"
            )
        return f"已回应 challenge_id={ch.challenge_id} verdict={verdict}"

    def _list_open(self, target: str) -> list[dict]:
        if target != self.issuer:
            raise ValueError(
                f"can only list challenges where target == self.issuer ({self.issuer!r}), got {target!r}"
            )
        session = get_session()
        try:
            rows = get_unresolved_challenges_for_run(
                session=session, run_id=self.run_id, target=self.issuer,
            )
        finally:
            session.close()
        return [
            {
                "challenge_id": ch.challenge_id,
                "issuer": ch.issuer,
                "target": ch.target,
                "claim": ch.claim,
                "reason": ch.reason,
            }
            for ch in rows
        ]


def make_challenge_tool(
    run_id: str, agent_name: str, max_challenges: int = 3,
) -> ChallengeTool:
    return ChallengeTool(
        run_id=run_id, issuer=agent_name, max_challenges=max_challenges,
    )
