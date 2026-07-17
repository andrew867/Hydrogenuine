"""Failure posture — fail-still, no fake success."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from hg_core.policy_safety.hashing import compute_record_hash

WORKSPACE = Path(__file__).resolve().parents[2]
DEFAULT_POLICY_PATH = WORKSPACE / "configs/agent_zero/failure_posture_policy.json"


class FailureKind(str, Enum):
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    LIVE_READ_UNAVAILABLE = "live_read_unavailable"
    WATCHTOWER_UNAVAILABLE = "watchtower_unavailable"
    EXCITON_STALE = "exciton_stale"
    QUEUE_UNAVAILABLE = "queue_unavailable"
    BROKER_UNAVAILABLE = "broker_unavailable"
    OUTPUT_VALIDATOR_UNAVAILABLE = "output_validator_unavailable"
    PROOF_BUNDLE_UNAVAILABLE = "proof_bundle_unavailable"
    CLOCK_UNCERTAIN = "clock_uncertain"
    BUDGET_UNCERTAIN = "budget_uncertain"
    STOP_PANIC_UNCERTAIN = "stop_panic_uncertain"
    UNKNOWN = "unknown"


class FailureSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class FailurePosture(str, Enum):
    CONTINUE_INTERNAL_ONLY = "continue_internal_only"
    DEFER_TURN = "defer_turn"
    REST_TURN = "rest_turn"
    FAIL_STILL = "fail_still"
    REQUEST_OPERATOR_REVIEW = "request_operator_review"
    PANIC_REQUIRED = "panic_required"


@dataclass(frozen=True)
class FailurePostureReceipt:
    receipt_id: str
    failure_kind: FailureKind
    severity: FailureSeverity
    posture: FailurePosture
    reason: str
    fake_success_denied: bool = True
    created_at: str = ""
    hash: str = ""

    def to_payload(self) -> dict[str, Any]:
        return {
            "receipt_id": self.receipt_id,
            "failure_kind": self.failure_kind.value,
            "severity": self.severity.value,
            "posture": self.posture.value,
            "reason": self.reason,
            "fake_success_denied": self.fake_success_denied,
            "created_at": self.created_at,
            "hash": self.hash,
        }


_POSTURE_MAP: dict[FailureKind, FailurePosture] = {
    FailureKind.PROVIDER_UNAVAILABLE: FailurePosture.FAIL_STILL,
    FailureKind.LIVE_READ_UNAVAILABLE: FailurePosture.FAIL_STILL,
    FailureKind.WATCHTOWER_UNAVAILABLE: FailurePosture.DEFER_TURN,
    FailureKind.EXCITON_STALE: FailurePosture.FAIL_STILL,
    FailureKind.QUEUE_UNAVAILABLE: FailurePosture.DEFER_TURN,
    FailureKind.BROKER_UNAVAILABLE: FailurePosture.FAIL_STILL,
    FailureKind.OUTPUT_VALIDATOR_UNAVAILABLE: FailurePosture.FAIL_STILL,
    FailureKind.PROOF_BUNDLE_UNAVAILABLE: FailurePosture.DEFER_TURN,
    FailureKind.CLOCK_UNCERTAIN: FailurePosture.FAIL_STILL,
    FailureKind.BUDGET_UNCERTAIN: FailurePosture.REQUEST_OPERATOR_REVIEW,
    FailureKind.STOP_PANIC_UNCERTAIN: FailurePosture.PANIC_REQUIRED,
    FailureKind.UNKNOWN: FailurePosture.FAIL_STILL,
}


def evaluate_failure_posture(
    *,
    failure_kind: FailureKind,
    detail: str = "",
) -> FailurePostureReceipt:
    """Map system failure to honest posture — no fake cognition or success."""
    posture = _POSTURE_MAP.get(failure_kind, FailurePosture.FAIL_STILL)
    severity = FailureSeverity.HIGH
    if failure_kind == FailureKind.STOP_PANIC_UNCERTAIN:
        severity = FailureSeverity.CRITICAL
    elif failure_kind in (FailureKind.WATCHTOWER_UNAVAILABLE, FailureKind.QUEUE_UNAVAILABLE):
        severity = FailureSeverity.MEDIUM

    reason = detail.strip() or f"{failure_kind.value} requires {posture.value}"
    rid = f"failure-posture-{uuid.uuid4().hex[:16]}"
    ts = datetime.now(timezone.utc).isoformat()
    body = {
        "receipt_id": rid,
        "failure_kind": failure_kind.value,
        "severity": severity.value,
        "posture": posture.value,
        "reason": reason,
        "fake_success_denied": True,
        "created_at": ts,
    }
    digest = compute_record_hash(body)
    return FailurePostureReceipt(
        receipt_id=rid,
        failure_kind=failure_kind,
        severity=severity,
        posture=posture,
        reason=reason,
        fake_success_denied=True,
        created_at=ts,
        hash=digest,
    )


def output_validator_failure_blocks_acceptance(receipt: FailurePostureReceipt) -> bool:
    """Output validator unavailable cannot accept draft output."""
    return (
        receipt.failure_kind == FailureKind.OUTPUT_VALIDATOR_UNAVAILABLE
        and receipt.posture in (FailurePosture.FAIL_STILL, FailurePosture.DEFER_TURN)
        and receipt.fake_success_denied
    )


def provider_failure_denies_cognition(receipt: FailurePostureReceipt) -> bool:
    """Provider failure cannot produce fake cognition."""
    return receipt.failure_kind == FailureKind.PROVIDER_UNAVAILABLE and receipt.fake_success_denied


def load_failure_posture_policy(*, path: Path | None = None) -> dict[str, Any]:
    policy_path = path or DEFAULT_POLICY_PATH
    if not policy_path.is_file():
        return {}
    return json.loads(policy_path.read_text(encoding="utf-8"))


__all__ = [
    "FailureKind",
    "FailurePosture",
    "FailurePostureReceipt",
    "FailureSeverity",
    "evaluate_failure_posture",
    "load_failure_posture_policy",
    "output_validator_failure_blocks_acceptance",
    "provider_failure_denies_cognition",
]
