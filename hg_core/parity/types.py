"""Evidence claim objects — path-stamped citations (CT-03 PAR)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class EvidenceClaim:
    """A report claim tied to a runtime path and optional proof reference."""

    claim_id: str
    path_id: str
    summary: str
    state_hash: str | None = None
    proof_ref: str | None = None
    subsystems: tuple[str, ...] = ()

    def to_payload(self) -> dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "path_id": self.path_id,
            "summary": self.summary,
            "state_hash": self.state_hash,
            "proof_ref": self.proof_ref,
            "subsystems": list(self.subsystems),
        }


__all__ = ["EvidenceClaim"]
