"""Task selection receipts — deterministic audit trail."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from hg_core.policy_safety.hashing import compute_record_hash
from hg_runtime.task_selection.schema import STORE_ROOT, new_id, now_iso

RECEIPT_DIR = STORE_ROOT / "receipts"
DECISION_DIR = STORE_ROOT / "decisions"


@dataclass
class TaskSelectionDecision:
    task_selection_decision_id: str
    universe_ref: str
    candidate_refs: tuple[str, ...]
    refused_candidate_refs: tuple[str, ...]
    deferred_candidate_refs: tuple[str, ...]
    selection_reason_code: str
    authority_boundary_ref: str
    verdict: str
    created_at: str
    selected_candidate_ref: str | None = None
    idle_reflection_ref: str | None = None
    broker_decision_ref: str | None = None
    hash: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "task_selection_decision_id": self.task_selection_decision_id,
            "universe_ref": self.universe_ref,
            "candidate_refs": list(self.candidate_refs),
            "selected_candidate_ref": self.selected_candidate_ref,
            "refused_candidate_refs": list(self.refused_candidate_refs),
            "deferred_candidate_refs": list(self.deferred_candidate_refs),
            "idle_reflection_ref": self.idle_reflection_ref,
            "selection_reason_code": self.selection_reason_code,
            "authority_boundary_ref": self.authority_boundary_ref,
            "broker_decision_ref": self.broker_decision_ref,
            "created_at": self.created_at,
            "verdict": self.verdict,
            "hash": self.hash,
        }

    def with_hash(self) -> TaskSelectionDecision:
        body = {k: v for k, v in self.to_payload().items() if k != "hash"}
        return TaskSelectionDecision(**{**self.__dict__, "hash": compute_record_hash(body)})


@dataclass
class TaskSelectionReceipt:
    task_selection_receipt_id: str
    decision_ref: str
    external_action_required: bool
    external_action_allowed: bool
    created_at: str
    selected_candidate_ref: str | None = None
    objective_scope_ref: str | None = None
    task_type: str | None = None
    hash: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "task_selection_receipt_id": self.task_selection_receipt_id,
            "decision_ref": self.decision_ref,
            "selected_candidate_ref": self.selected_candidate_ref,
            "objective_scope_ref": self.objective_scope_ref,
            "task_type": self.task_type,
            "external_action_required": self.external_action_required,
            "external_action_allowed": self.external_action_allowed,
            "created_at": self.created_at,
            "hash": self.hash,
        }

    def with_hash(self) -> TaskSelectionReceipt:
        body = {k: v for k, v in self.to_payload().items() if k != "hash"}
        return TaskSelectionReceipt(**{**self.__dict__, "hash": compute_record_hash(body)})


@dataclass
class TaskSwitchReceipt:
    task_switch_receipt_id: str
    from_task_ref: str | None
    to_task_ref: str
    decision_ref: str
    created_at: str
    hash: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "task_switch_receipt_id": self.task_switch_receipt_id,
            "from_task_ref": self.from_task_ref,
            "to_task_ref": self.to_task_ref,
            "decision_ref": self.decision_ref,
            "created_at": self.created_at,
            "hash": self.hash,
        }

    def with_hash(self) -> TaskSwitchReceipt:
        body = {k: v for k, v in self.to_payload().items() if k != "hash"}
        return TaskSwitchReceipt(**{**self.__dict__, "hash": compute_record_hash(body)})


@dataclass
class IdleReflectionReceipt:
    idle_reflection_receipt_id: str
    universe_ref: str
    reason_code: str
    created_at: str
    hash: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "idle_reflection_receipt_id": self.idle_reflection_receipt_id,
            "universe_ref": self.universe_ref,
            "reason_code": self.reason_code,
            "created_at": self.created_at,
            "hash": self.hash,
        }

    def with_hash(self) -> IdleReflectionReceipt:
        body = {k: v for k, v in self.to_payload().items() if k != "hash"}
        return IdleReflectionReceipt(**{**self.__dict__, "hash": compute_record_hash(body)})


def persist_decision(decision: TaskSelectionDecision) -> Path:
    DECISION_DIR.mkdir(parents=True, exist_ok=True)
    path = DECISION_DIR / f"{decision.task_selection_decision_id}.json"
    path.write_text(json.dumps(decision.to_payload(), indent=2) + "\n", encoding="utf-8")
    return path


def persist_selection_receipt(receipt: TaskSelectionReceipt) -> Path:
    RECEIPT_DIR.mkdir(parents=True, exist_ok=True)
    path = RECEIPT_DIR / f"{receipt.task_selection_receipt_id}.json"
    path.write_text(json.dumps(receipt.to_payload(), indent=2) + "\n", encoding="utf-8")
    return path


def persist_switch_receipt(receipt: TaskSwitchReceipt) -> Path:
    RECEIPT_DIR.mkdir(parents=True, exist_ok=True)
    path = RECEIPT_DIR / f"{receipt.task_switch_receipt_id}.json"
    path.write_text(json.dumps(receipt.to_payload(), indent=2) + "\n", encoding="utf-8")
    return path


def persist_idle_receipt(receipt: IdleReflectionReceipt) -> Path:
    RECEIPT_DIR.mkdir(parents=True, exist_ok=True)
    path = RECEIPT_DIR / f"{receipt.idle_reflection_receipt_id}.json"
    path.write_text(json.dumps(receipt.to_payload(), indent=2) + "\n", encoding="utf-8")
    return path
