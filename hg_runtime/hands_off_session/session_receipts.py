"""Session receipts — continuous turn and start receipts."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from hg_core.policy_safety.hashing import compute_record_hash
from hg_runtime.hands_off_session.schema import new_id, now_iso, session_dir


@dataclass
class ContinuousTurnReceipt:
    continuous_turn_receipt_id: str
    session_id: str
    turn_index: int
    turn_receipt_ref: str
    task_selection_receipt_ref: str
    broker_decision_ref: str | None
    selected_task_type: str | None
    verdict: str
    external_side_effect: bool
    created_at: str
    governed_work_receipt_ref: str | None = None
    hash: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "continuous_turn_receipt_id": self.continuous_turn_receipt_id,
            "session_id": self.session_id,
            "turn_index": self.turn_index,
            "turn_receipt_ref": self.turn_receipt_ref,
            "task_selection_receipt_ref": self.task_selection_receipt_ref,
            "broker_decision_ref": self.broker_decision_ref,
            "selected_task_type": self.selected_task_type,
            "verdict": self.verdict,
            "external_side_effect": self.external_side_effect,
            "governed_work_receipt_ref": self.governed_work_receipt_ref,
            "created_at": self.created_at,
            "hash": self.hash,
        }

    def with_hash(self) -> ContinuousTurnReceipt:
        body = {k: v for k, v in self.to_payload().items() if k != "hash"}
        return ContinuousTurnReceipt(**{**self.__dict__, "hash": compute_record_hash(body)})


def receipts_dir(session_id: str, *, base: Path | None = None) -> Path:
    return session_dir(session_id, base=base) / "receipts"


def persist_continuous_turn_receipt(receipt: ContinuousTurnReceipt, *, base: Path | None = None) -> Path:
    d = receipts_dir(receipt.session_id, base=base)
    d.mkdir(parents=True, exist_ok=True)
    path = d / f"{receipt.continuous_turn_receipt_id}.json"
    path.write_text(json.dumps(receipt.to_payload(), indent=2) + "\n", encoding="utf-8")
    return path


def list_continuous_turn_receipts(session_id: str, *, base: Path | None = None) -> list[ContinuousTurnReceipt]:
    d = receipts_dir(session_id, base=base)
    out: list[ContinuousTurnReceipt] = []
    if not d.is_dir():
        return out
    for p in sorted(d.glob("cont-turn-*.json")):
        data = json.loads(p.read_text(encoding="utf-8"))
        out.append(ContinuousTurnReceipt(**data))
    out.sort(key=lambda r: r.turn_index)
    return out


def persist_start_receipt(session_id: str, config_hash: str, *, base: Path | None = None) -> Path:
    d = receipts_dir(session_id, base=base)
    d.mkdir(parents=True, exist_ok=True)
    payload = {
        "start_receipt_id": new_id("sess-start"),
        "session_id": session_id,
        "config_hash": config_hash,
        "created_at": now_iso(),
        "foreground": True,
        "scheduler_allowed": False,
        "daemon_allowed": False,
    }
    path = d / "session_start.json"
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path
