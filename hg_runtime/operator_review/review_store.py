"""Local operator review store."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from hg_runtime.operator_review.audit_log import append_audit_entry, read_audit_log
from hg_runtime.operator_review.errors import ReviewStoreError
from hg_runtime.operator_review.redaction import has_forbidden_review_field
from hg_runtime.operator_review.schema import (
    OperatorReviewDecision,
    OperatorReviewDecisionReceipt,
    OperatorReviewItem,
    OperatorReviewQueueSnapshot,
    ReviewItemTruthState,
)


def review_root(*, base: Path | None = None) -> Path:
    env_root = os.environ.get("HG_REVIEW_ROOT")
    if env_root:
        return Path(env_root)
    root = base or Path(__file__).resolve().parents[2] / ".hg-local" / "agent_zero" / "review"
    return root


def run_review_dir(run_id: str, *, base: Path | None = None) -> Path:
    return review_root(base=base) / run_id


def _write_atomic(path: Path, payload: dict[str, Any]) -> Path:
    if has_forbidden_review_field(payload):
        raise ReviewStoreError("payload contains forbidden field")
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise ReviewStoreError(f"record already exists: {path}")
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)
    return path


def _write_overwrite(path: Path, payload: dict[str, Any]) -> Path:
    if has_forbidden_review_field(payload):
        raise ReviewStoreError("payload contains forbidden field")
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)
    return path


@dataclass
class ReviewStore:
    run_id: str
    base: Path | None = None

    @property
    def root(self) -> Path:
        return run_review_dir(self.run_id, base=self.base)

    @property
    def items_dir(self) -> Path:
        return self.root / "review_items"

    @property
    def receipts_dir(self) -> Path:
        return self.root / "decision_receipts"

    @property
    def truth_dir(self) -> Path:
        return self.root / "truth_states"

    @property
    def snapshot_path(self) -> Path:
        return self.root / "queue_snapshot.json"

    @property
    def audit_log_path(self) -> Path:
        return self.root / "audit_log.jsonl"

    def store_snapshot(self, snapshot: OperatorReviewQueueSnapshot) -> Path:
        return _write_overwrite(self.snapshot_path, snapshot.to_payload())

    def read_snapshot(self) -> dict[str, Any] | None:
        if not self.snapshot_path.is_file():
            return None
        return json.loads(self.snapshot_path.read_text(encoding="utf-8"))

    def store_review_item(self, item: OperatorReviewItem) -> Path:
        return _write_atomic(self.items_dir / f"{item.review_item_id}.json", item.to_payload())

    def update_review_item(self, item: OperatorReviewItem) -> Path:
        path = self.items_dir / f"{item.review_item_id}.json"
        if not path.is_file():
            raise ReviewStoreError(f"review item not found: {item.review_item_id}")
        return _write_overwrite(path, item.to_payload())

    def read_review_item(self, review_item_id: str) -> dict[str, Any]:
        path = self.items_dir / f"{review_item_id}.json"
        if not path.is_file():
            raise ReviewStoreError(f"review item not found: {review_item_id}")
        return json.loads(path.read_text(encoding="utf-8"))

    def find_item_by_candidate(self, candidate_ref: str) -> dict[str, Any] | None:
        if not self.items_dir.is_dir():
            return None
        for path in self.items_dir.glob("*.json"):
            payload = json.loads(path.read_text(encoding="utf-8"))
            if payload.get("candidate_ref") == candidate_ref:
                return payload
        return None

    def store_truth_state(self, truth: ReviewItemTruthState) -> Path:
        return _write_atomic(self.truth_dir / f"{truth.truth_state_id}.json", truth.to_payload())

    def read_truth_state(self, truth_state_id: str) -> dict[str, Any]:
        path = self.truth_dir / f"{truth_state_id}.json"
        if not path.is_file():
            raise ReviewStoreError(f"truth state not found: {truth_state_id}")
        return json.loads(path.read_text(encoding="utf-8"))

    def store_decision_receipt(self, receipt: OperatorReviewDecisionReceipt) -> Path:
        path = _write_atomic(self.receipts_dir / f"{receipt.decision_receipt_id}.json", receipt.to_payload())
        append_audit_entry(
            self.audit_log_path,
            {
                "kind": "decision_receipt",
                "decision_receipt_id": receipt.decision_receipt_id,
                "decision_ref": receipt.decision_ref,
                "review_item_ref": receipt.review_item_ref,
                "action_receipt_hash": receipt.hash,
                "external_side_effect": receipt.external_side_effect,
                "published": receipt.published,
                "sent": receipt.sent,
            },
        )
        return path

    def store_decision(self, decision: OperatorReviewDecision) -> Path:
        path = _write_atomic(self.receipts_dir / f"{decision.decision_id}.json", decision.to_payload())
        append_audit_entry(
            self.audit_log_path,
            {
                "kind": "decision",
                "decision_id": decision.decision_id,
                "review_item_ref": decision.review_item_ref,
                "action": decision.action.value,
                "decision_hash": decision.hash,
            },
        )
        return path

    def list_decision_receipts(self) -> list[dict[str, Any]]:
        if not self.receipts_dir.is_dir():
            return []
        out = []
        for path in sorted(self.receipts_dir.glob("review-receipt-*.json")):
            out.append(json.loads(path.read_text(encoding="utf-8")))
        return out

    def read_audit(self) -> list[dict[str, Any]]:
        return read_audit_log(self.audit_log_path)


__all__ = ["ReviewStore", "review_root", "run_review_dir"]
