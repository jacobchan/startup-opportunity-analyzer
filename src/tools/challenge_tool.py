from crewai.tools import BaseTool

from src.storage import add_challenge, get_session


class ChallengeTool(BaseTool):
    name: str = "challenge"
    description: str = (
        "对其他 agent 的结论提出挑战。"
        "输入: target (被挑战的 agent 名), claim (被挑战的具体论断), reason (挑战理由)。"
    )
    run_id: str
    issuer: str
    _count: int = 0
    max_challenges: int = 3

    def _run(self, target: str, claim: str, reason: str) -> str:
        if not claim.strip():
            raise ValueError("claim cannot be empty")
        if target == self.issuer:
            raise ValueError("cannot challenge yourself")
        if self._count >= self.max_challenges:
            raise RuntimeError(f"max challenges ({self.max_challenges}) reached for {self.issuer}")
        session = get_session()
        ch = add_challenge(
            session=session,
            run_id=self.run_id,
            issuer=self.issuer,
            target=target,
            claim=claim,
            reason=reason,
        )
        self._count += 1
        return f"挑战已发出 challenge_id={ch.challenge_id}，等待 {target} 回应"


def make_challenge_tool(run_id: str, agent_name: str, max_challenges: int = 3) -> ChallengeTool:
    return ChallengeTool(run_id=run_id, issuer=agent_name, max_challenges=max_challenges)
