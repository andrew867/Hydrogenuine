"""Pre-EXCITON boundary schema."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

FROZEN_FALSE = {
    "advisory_only": True,
    "permission_granted": False,
    "authority_created": False,
}


class BoundaryVerdict(str, Enum):
    ALLOW = "ALLOW"
    DEFER = "DEFER"
    BLOCK = "BLOCK"


@dataclass
class BoundaryDecision:
    verdict: BoundaryVerdict
    reason: str
    boundary: str

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema": "pre-exciton-boundary-decision",
            "verdict": self.verdict.value,
            "reason": self.reason,
            "boundary": self.boundary,
            **FROZEN_FALSE,
        }
