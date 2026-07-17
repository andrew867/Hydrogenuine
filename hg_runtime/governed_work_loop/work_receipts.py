"""Governed work receipts."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from hg_core.policy_safety.hashing import compute_record_hash
from hg_runtime.governed_work_loop.schema import STORE_ROOT, new_id, now_iso

RECEIPT_DIR = STORE_ROOT / "receipts"
DECISION_DIR = STORE_ROOT / "decisions"


@dataclass
class GovernedWorkDecision:
    governed_work_decision_id: str
    work_item_ref: str
    verdict: str
    refusal_reason: str | None
    broker_decision_ref: str | None
    external_candidate_ref: str | None
    authority_request_ref: str | None
    dispatch_decision_ref: str | None
    created_at: str
    hash: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "governed_work_decision_id": self.governed_work_decision_id,
            "work_item_ref": self.work_item_ref,
            "verdict": self.verdict,
            "refusal_reason": self.refusal_reason,
            "broker_decision_ref": self.broker_decision_ref,
            "external_candidate_ref": self.external_candidate_ref,
            "authority_request_ref": self.authority_request_ref,
            "dispatch_decision_ref": self.dispatch_decision_ref,
            "created_at": self.created_at,
            "hash": self.hash,
        }

    def with_hash(self) -> GovernedWorkDecision:
        body = {k: v for k, v in self.to_payload().items() if k != "hash"}
        return GovernedWorkDecision(**{**self.__dict__, "hash": compute_record_hash(body)})


@dataclass
class GovernedWorkReceipt:
    governed_work_receipt_id: str
    decision_ref: str
    work_item_ref: str
    task_selection_ref: str
    work_type: str
    external_side_effect: bool
    verdict: str
    created_at: str
    broker_decision_ref: str | None = None
    external_candidate_ref: str | None = None
    dry_dispatch_ref: str | None = None
    hash: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "governed_work_receipt_id": self.governed_work_receipt_id,
            "decision_ref": self.decision_ref,
            "work_item_ref": self.work_item_ref,
            "task_selection_ref": self.task_selection_ref,
            "work_type": self.work_type,
            "external_side_effect": self.external_side_effect,
            "verdict": self.verdict,
            "broker_decision_ref": self.broker_decision_ref,
            "external_candidate_ref": self.external_candidate_ref,
            "dry_dispatch_ref": self.dry_dispatch_ref,
            "created_at": self.created_at,
            "hash": self.hash,
        }

    def with_hash(self) -> GovernedWorkReceipt:
        body = {k: v for k, v in self.to_payload().items() if k != "hash"}
        return GovernedWorkReceipt(**{**self.__dict__, "hash": compute_record_hash(body)})


def persist_decision(decision: GovernedWorkDecision) -> Path:
    DECISION_DIR.mkdir(parents=True, exist_ok=True)
    path = DECISION_DIR / f"{decision.governed_work_decision_id}.json"
    path.write_text(json.dumps(decision.to_payload(), indent=2) + "\n", encoding="utf-8")
    return path


def persist_receipt(receipt: GovernedWorkReceipt) -> Path:
    RECEIPT_DIR.mkdir(parents=True, exist_ok=True)
    path = RECEIPT_DIR / f"{receipt.governed_work_receipt_id}.json"
    path.write_text(json.dumps(receipt.to_payload(), indent=2) + "\n", encoding="utf-8")
    return path
