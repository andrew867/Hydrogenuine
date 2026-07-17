"""Operator decision receipts carrying authenticated identity. Hashed + chainable."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Optional

from hg_core.governance.canonical_hash import canonical_hash
from hg_operator_auth.identity import (
    OperatorIdentity, OperatorIdentityError, validate_operator_identity,
)

OPERATOR_DECISION_SCHEMA = "hg-operator-decision-receipt"
OPERATOR_DECISION_SCHEMA_VERSION = "1.0"
_JWT_RE = re.compile(r"eyJ[A-Za-z0-9_-]{10,}")


class OperatorReceiptError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class OperatorDecisionReceipt:
    receipt_id: str
    decided_at: str
    decision: str                        # "approve" | "deny"
    action_class: str
    risk_category: str
    target_ref: str                      # what was approved/denied (claim id, run id…)
    reason: str
    operator_identity: OperatorIdentity
    step_up_required: bool
    step_up_satisfied: bool
    breakglass_reason: str = ""
    previous_receipt_hash: Optional[str] = None
    receipt_hash: str = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "receipt_hash", canonical_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": OPERATOR_DECISION_SCHEMA,
            "schema_version": OPERATOR_DECISION_SCHEMA_VERSION,
            "receipt_id": self.receipt_id,
            "decided_at": self.decided_at,
            "decision": self.decision,
            "action_class": self.action_class,
            "risk_category": self.risk_category,
            "target_ref": self.target_ref,
            "reason": self.reason,
            "operator_identity": self.operator_identity.to_payload(),
            "step_up_required": self.step_up_required,
            "step_up_satisfied": self.step_up_satisfied,
            "breakglass_reason": self.breakglass_reason,
            "previous_receipt_hash": self.previous_receipt_hash,
        }
        if include_hash:
            payload["receipt_hash"] = self.receipt_hash
        return payload


def validate_operator_decision_receipt(receipt: OperatorDecisionReceipt) -> None:
    """Fail closed: identity invariants + no raw tokens + step-up consistency."""
    try:
        validate_operator_identity(receipt.operator_identity)
    except OperatorIdentityError as exc:
        raise OperatorReceiptError(exc.code) from exc
    if receipt.decision not in ("approve", "deny"):
        raise OperatorReceiptError("unknown_decision")
    if receipt.step_up_satisfied and not receipt.operator_identity.step_up_evidence:
        raise OperatorReceiptError("step_up_satisfied_without_evidence")
    if receipt.action_class == "breakglass" and receipt.decision == "approve" \
            and not receipt.breakglass_reason.strip():
        raise OperatorReceiptError("breakglass_reason_required")
    if _JWT_RE.search(str(receipt.to_payload())):
        raise OperatorReceiptError("raw_token_in_receipt")
    expected = canonical_hash(receipt.to_payload(include_hash=False))
    if receipt.receipt_hash != expected:
        raise OperatorReceiptError("receipt_hash_mismatch")


def verify_receipt_chain(payloads: list[dict[str, Any]]) -> dict[str, Any]:
    """Recompute hashes + previous_receipt_hash linkage over serialized receipts."""
    failures: list[str] = []
    previous: Optional[str] = None
    for index, payload in enumerate(payloads):
        body = dict(payload)
        stored = body.pop("receipt_hash", "")
        if canonical_hash(body) != stored:
            failures.append(f"hash_mismatch_at_{index}")
        if body.get("previous_receipt_hash") != previous:
            failures.append(f"link_broken_at_{index}")
        previous = stored
    return {"ok": not failures, "count": len(payloads), "failures": failures}


def demo_local_identity(*, operator_id: str, display_name: str = "Demo Operator") -> OperatorIdentity:
    """Demo-local signed operator — NEVER production auth (validator-enforced)."""
    return OperatorIdentity(
        provider="demo_local",
        issuer="demo-local",
        subject=operator_id,
        display_name=display_name,
        email="",
        roles=("hg.operator", "hg.approver"),
        session_id_hash="",
        auth_time=None,
        assurance_level="demo_local",
        step_up_required=False,
        step_up_satisfied=False,
        production_operator_auth=False,
        demo_local_signing=True,
    )


__all__ = ["OPERATOR_DECISION_SCHEMA", "OPERATOR_DECISION_SCHEMA_VERSION",
           "OperatorDecisionReceipt", "OperatorReceiptError", "demo_local_identity",
           "validate_operator_decision_receipt", "verify_receipt_chain"]
