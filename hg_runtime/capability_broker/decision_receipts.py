"""Broker decision receipts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from hg_runtime.agent_zero_state.hashing import hash_record, verify_record_hash
from hg_runtime.capability_broker.action_registry import registry_hash
from hg_runtime.capability_broker.redaction import scan_broker_payload
from hg_runtime.capability_broker.schema import BrokerDecision, BrokerRequest, BrokerVerdict


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class DecisionReceipt:
    decision_receipt_id: str
    broker_decision_ref: str
    request_hash: str
    decision_hash: str
    policy_hash: str
    action_registry_hash: str
    requirements_checked: dict[str, Any]
    refusal_reasons: list[str]
    created_at: str
    hash: str = ""
    dispatch_plan_ref: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "decision_receipt_id": self.decision_receipt_id,
            "broker_decision_ref": self.broker_decision_ref,
            "request_hash": self.request_hash,
            "decision_hash": self.decision_hash,
            "policy_hash": self.policy_hash,
            "action_registry_hash": self.action_registry_hash,
            "requirements_checked": dict(self.requirements_checked),
            "refusal_reasons": list(self.refusal_reasons),
            "dispatch_plan_ref": self.dispatch_plan_ref,
            "created_at": self.created_at,
            "hash": self.hash,
        }

    def with_hash(self) -> DecisionReceipt:
        body = {k: v for k, v in self.to_payload().items() if k != "hash"}
        return DecisionReceipt(**{**self.__dict__, "hash": hash_record(body)})


def build_decision_receipt(
    *,
    request: BrokerRequest,
    decision: BrokerDecision,
    policy_hash: str,
    dispatch_plan_ref: str | None = None,
) -> DecisionReceipt:
    rid = f"dec-rcpt-{hash_record({'decision': decision.decision_id, 'request': request.request_id})[7:19]}"
    receipt = DecisionReceipt(
        decision_receipt_id=rid,
        broker_decision_ref=decision.decision_id,
        request_hash=request.hash,
        decision_hash=decision.hash,
        policy_hash=policy_hash,
        action_registry_hash=registry_hash(),
        requirements_checked=dict(decision.requirements_checked),
        refusal_reasons=list(decision.refusal_reasons),
        dispatch_plan_ref=dispatch_plan_ref,
        created_at=decision.created_at,
    ).with_hash()
    return validate_decision_receipt(receipt)


def validate_decision_receipt(receipt: DecisionReceipt) -> DecisionReceipt:
    has_secret, has_cot = scan_broker_payload(receipt.to_payload())
    if has_secret:
        raise ValueError(BrokerVerdict.RED_BROKER_SECRET_LEAK.value)
    if has_cot:
        raise ValueError(BrokerVerdict.RED_BROKER_COT_LEAK.value)
    if not receipt.hash or not verify_record_hash(
        {k: v for k, v in receipt.to_payload().items() if k != "hash"}, receipt.hash
    ):
        raise ValueError("decision receipt hash invalid")
    if not receipt.decision_hash or not receipt.request_hash:
        raise ValueError("decision receipt missing hashes")
    return receipt


__all__ = [
    "DecisionReceipt",
    "build_decision_receipt",
    "validate_decision_receipt",
]
