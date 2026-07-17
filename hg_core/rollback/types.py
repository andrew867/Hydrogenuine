"""Rollback drill types (CT-07 RBK)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

DrillId = Literal["D1", "D2", "D3", "D4", "D5", "D6", "D7", "D8", "D9", "D10"]


@dataclass(frozen=True)
class DrillReceipt:
    receipt_id: str
    drill_id: str
    action: str
    reason_code: str
    evidence_hash: str
    lockdown: bool = False

    def to_payload(self) -> dict[str, Any]:
        return {
            "receipt_id": self.receipt_id,
            "drill_id": self.drill_id,
            "action": self.action,
            "reason_code": self.reason_code,
            "evidence_hash": self.evidence_hash,
            "lockdown": self.lockdown,
        }


@dataclass(frozen=True)
class DrillOutcome:
    drill_id: DrillId
    ok: bool
    verdict: str  # pass | fail | not_proven
    reason_code: str
    receipts: tuple[DrillReceipt, ...] = field(default_factory=tuple)
    detail: dict[str, Any] = field(default_factory=dict)

    def to_payload(self) -> dict[str, Any]:
        return {
            "drill_id": self.drill_id,
            "ok": self.ok,
            "verdict": self.verdict,
            "reason_code": self.reason_code,
            "receipts": [r.to_payload() for r in self.receipts],
            "detail": self.detail,
        }


__all__ = ["DrillId", "DrillOutcome", "DrillReceipt"]
