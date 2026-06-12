from dataclasses import dataclass
from enum import Enum


class Verdict(str, Enum):
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    MODIFIED = "modified"


@dataclass
class ChallengeDraft:
    issuer: str
    target: str
    claim: str
    reason: str

    def __post_init__(self):
        if not self.claim.strip():
            raise ValueError("claim cannot be empty")
        if self.issuer == self.target:
            raise ValueError("issuer and target must differ")
