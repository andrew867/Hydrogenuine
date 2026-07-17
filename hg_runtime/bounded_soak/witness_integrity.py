"""Witness integrity layer — receipt posture, not permission organ."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from hg_core.policy_safety.hashing import compute_record_hash

WORKSPACE = Path(__file__).resolve().parents[2]
DEFAULT_POLICY_PATH = WORKSPACE / "configs/agent_zero/witness_integrity_policy.json"


class WitnessMode(str, Enum):
    OBSERVE_ONLY = "observe_only"
    REST = "rest"
    FAIL_STILL = "fail_still"
    OPERATOR_ABSENT = "operator_absent"
    SCOPE_EXCEEDED = "scope_exceeded"
    SYSTEM_UNAVAILABLE = "system_unavailable"
    STALE_WORLD = "stale_world"
    UNCERTAIN = "uncertain"


class WitnessReason(str, Enum):
    OPERATOR_ABSENT = "operator_absent"
    SYSTEM_FAILURE = "system_failure"
    SCOPE_EXCEEDED = "scope_exceeded"
    STALE_WORLD = "stale_world"
    REST_CHOSEN = "rest_chosen"
    FAIL_STILL_REQUIRED = "fail_still_required"
    UNCERTAIN_STATE = "uncertain_state"
    OBSERVE_ONLY = "observe_only"


class WitnessIntegrityVerdict(str, Enum):
    GREEN_WITNESS_RECEIPT_VALID = "GREEN_WITNESS_RECEIPT_VALID"
    YELLOW_WITNESS_MODE_ENTERED = "YELLOW_WITNESS_MODE_ENTERED"
    YELLOW_OPERATOR_ABSENT_INTERNAL_ONLY = "YELLOW_OPERATOR_ABSENT_INTERNAL_ONLY"
    YELLOW_SCOPE_REQUEST_REQUIRED = "YELLOW_SCOPE_REQUEST_REQUIRED"
    YELLOW_FAIL_STILL_ENTERED = "YELLOW_FAIL_STILL_ENTERED"
    RED_WITNESS_EXPANDED_AUTHORITY = "RED_WITNESS_EXPANDED_AUTHORITY"
    RED_WITNESS_EXTERNAL_ACTION = "RED_WITNESS_EXTERNAL_ACTION"
    RED_WITNESS_STOP_PANIC_BYPASS = "RED_WITNESS_STOP_PANIC_BYPASS"
    RED_WITNESS_RECEIPT_EMPTY = "RED_WITNESS_RECEIPT_EMPTY"


@dataclass(frozen=True)
class WitnessIntegrityReceipt:
    receipt_id: str
    mode: WitnessMode
    reason: str
    operator_present: bool
    external_action_allowed: bool = False
    authority_expanded: bool = False
    stop_panic_override: bool = False
    turn_ref: str | None = None
    run_ref: str | None = None
    scope_request_refs: tuple[str, ...] = ()
    failure_posture_ref: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    hash: str = ""

    def to_payload(self) -> dict[str, Any]:
        return {
            "receipt_id": self.receipt_id,
            "turn_ref": self.turn_ref,
            "run_ref": self.run_ref,
            "mode": self.mode.value,
            "reason": self.reason,
            "operator_present": self.operator_present,
            "external_action_allowed": self.external_action_allowed,
            "authority_expanded": self.authority_expanded,
            "stop_panic_override": self.stop_panic_override,
            "scope_request_refs": list(self.scope_request_refs),
            "failure_posture_ref": self.failure_posture_ref,
            "created_at": self.created_at,
            "hash": self.hash,
        }


def _load_policy(path: Path | None = None) -> dict[str, Any]:
    policy_path = path or DEFAULT_POLICY_PATH
    if not policy_path.is_file():
        return {}
    return json.loads(policy_path.read_text(encoding="utf-8"))


def enter_witness_mode(
    *,
    mode: WitnessMode,
    reason: str,
    operator_present: bool = False,
    turn_ref: str | None = None,
    run_ref: str | None = None,
    scope_request_refs: list[str] | None = None,
    failure_posture_ref: str | None = None,
) -> tuple[WitnessIntegrityVerdict, WitnessIntegrityReceipt]:
    """Enter witness posture — internal-only, no authority expansion."""
    if not reason or not reason.strip():
        empty = WitnessIntegrityReceipt(
            receipt_id=f"witness-empty-{uuid.uuid4().hex[:12]}",
            mode=mode,
            reason="",
            operator_present=operator_present,
        )
        return WitnessIntegrityVerdict.RED_WITNESS_RECEIPT_EMPTY, empty

    verdict = WitnessIntegrityVerdict.YELLOW_WITNESS_MODE_ENTERED
    if mode == WitnessMode.OPERATOR_ABSENT:
        verdict = WitnessIntegrityVerdict.YELLOW_OPERATOR_ABSENT_INTERNAL_ONLY
    elif mode == WitnessMode.SCOPE_EXCEEDED:
        verdict = WitnessIntegrityVerdict.YELLOW_SCOPE_REQUEST_REQUIRED
    elif mode in (WitnessMode.FAIL_STILL, WitnessMode.SYSTEM_UNAVAILABLE):
        verdict = WitnessIntegrityVerdict.YELLOW_FAIL_STILL_ENTERED

    receipt = build_witness_receipt(
        mode=mode,
        reason=reason.strip(),
        operator_present=operator_present,
        turn_ref=turn_ref,
        run_ref=run_ref,
        scope_request_refs=scope_request_refs or [],
        failure_posture_ref=failure_posture_ref,
    )
    return verdict, receipt


def build_witness_receipt(
    *,
    mode: WitnessMode,
    reason: str,
    operator_present: bool,
    turn_ref: str | None = None,
    run_ref: str | None = None,
    scope_request_refs: list[str] | None = None,
    failure_posture_ref: str | None = None,
    receipt_id: str | None = None,
    created_at: str | None = None,
) -> WitnessIntegrityReceipt:
    """Build witness receipt with enforced safety invariants."""
    rid = receipt_id or f"witness-{uuid.uuid4().hex[:16]}"
    ts = created_at or datetime.now(timezone.utc).isoformat()
    body = {
        "receipt_id": rid,
        "turn_ref": turn_ref,
        "run_ref": run_ref,
        "mode": mode.value,
        "reason": reason,
        "operator_present": operator_present,
        "external_action_allowed": False,
        "authority_expanded": False,
        "stop_panic_override": False,
        "scope_request_refs": list(scope_request_refs or []),
        "failure_posture_ref": failure_posture_ref,
        "created_at": ts,
    }
    digest = compute_record_hash(body)
    return WitnessIntegrityReceipt(
        receipt_id=rid,
        mode=mode,
        reason=reason,
        operator_present=operator_present,
        external_action_allowed=False,
        authority_expanded=False,
        stop_panic_override=False,
        turn_ref=turn_ref,
        run_ref=run_ref,
        scope_request_refs=tuple(scope_request_refs or []),
        failure_posture_ref=failure_posture_ref,
        created_at=ts,
        hash=digest,
    )


def validate_witness_receipt(receipt: WitnessIntegrityReceipt) -> WitnessIntegrityVerdict:
    """Validate witness receipt invariants."""
    if not receipt.reason or not receipt.reason.strip():
        return WitnessIntegrityVerdict.RED_WITNESS_RECEIPT_EMPTY
    if receipt.external_action_allowed:
        return WitnessIntegrityVerdict.RED_WITNESS_EXTERNAL_ACTION
    if receipt.authority_expanded:
        return WitnessIntegrityVerdict.RED_WITNESS_EXPANDED_AUTHORITY
    if receipt.stop_panic_override:
        return WitnessIntegrityVerdict.RED_WITNESS_STOP_PANIC_BYPASS
    expected = compute_record_hash(receipt.to_payload())
    if receipt.hash and receipt.hash != expected:
        return WitnessIntegrityVerdict.RED_WITNESS_RECEIPT_EMPTY
    return WitnessIntegrityVerdict.GREEN_WITNESS_RECEIPT_VALID


__all__ = [
    "WitnessIntegrityReceipt",
    "WitnessIntegrityVerdict",
    "WitnessMode",
    "WitnessReason",
    "build_witness_receipt",
    "enter_witness_mode",
    "validate_witness_receipt",
]
