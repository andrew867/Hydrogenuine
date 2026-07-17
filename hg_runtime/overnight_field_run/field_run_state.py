"""Overnight field run state persistence."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from hg_core.policy_safety.hashing import compute_record_hash
from hg_runtime.overnight_field_run.schema import FieldRunStatus, field_run_dir, now_iso


@dataclass
class OvernightFieldRunState:
    field_run_id: str
    pid: int
    mode: str
    status: str = FieldRunStatus.STARTING.value
    started_at: str = ""
    stopped_at: str | None = None
    turn_count: int = 0
    task_selection_count: int = 0
    governed_work_count: int = 0
    internal_work_count: int = 0
    external_candidate_count: int = 0
    dry_dispatch_count: int = 0
    live_dispatch_count: int = 0
    refusal_count: int = 0
    idle_count: int = 0
    checkpoint_count: int = 0
    panic_count: int = 0
    last_selected_task_type: str = ""
    last_work_item_ref: str = ""
    last_turn_receipt_ref: str = ""
    last_task_selection_ref: str = ""
    last_governed_work_ref: str = ""
    last_heartbeat_ref: str = ""
    last_checkpoint_ref: str = ""
    stop_requested: bool = False
    panic_requested: bool = False
    external_side_effect_count: int = 0
    hands_off_session_id: str = ""
    hash: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "field_run_id": self.field_run_id,
            "pid": self.pid,
            "mode": self.mode,
            "status": self.status,
            "started_at": self.started_at,
            "stopped_at": self.stopped_at,
            "turn_count": self.turn_count,
            "task_selection_count": self.task_selection_count,
            "governed_work_count": self.governed_work_count,
            "internal_work_count": self.internal_work_count,
            "external_candidate_count": self.external_candidate_count,
            "dry_dispatch_count": self.dry_dispatch_count,
            "live_dispatch_count": self.live_dispatch_count,
            "refusal_count": self.refusal_count,
            "idle_count": self.idle_count,
            "checkpoint_count": self.checkpoint_count,
            "panic_count": self.panic_count,
            "last_selected_task_type": self.last_selected_task_type,
            "last_work_item_ref": self.last_work_item_ref,
            "last_turn_receipt_ref": self.last_turn_receipt_ref,
            "last_task_selection_ref": self.last_task_selection_ref,
            "last_governed_work_ref": self.last_governed_work_ref,
            "last_heartbeat_ref": self.last_heartbeat_ref,
            "last_checkpoint_ref": self.last_checkpoint_ref,
            "stop_requested": self.stop_requested,
            "panic_requested": self.panic_requested,
            "external_side_effect_count": self.external_side_effect_count,
            "hands_off_session_id": self.hands_off_session_id,
            "hash": self.hash,
        }

    def with_hash(self) -> OvernightFieldRunState:
        body = {k: v for k, v in self.to_payload().items() if k != "hash"}
        return OvernightFieldRunState(**{**self.__dict__, "hash": compute_record_hash(body)})


def persist_state(state: OvernightFieldRunState, *, base: Path | None = None) -> Path:
    root = field_run_dir(state.field_run_id, base=base)
    root.mkdir(parents=True, exist_ok=True)
    path = root / "state.json"
    path.write_text(json.dumps(state.with_hash().to_payload(), indent=2) + "\n", encoding="utf-8")
    return path


def load_state(field_run_id: str, *, base: Path | None = None) -> OvernightFieldRunState | None:
    path = field_run_dir(field_run_id, base=base) / "state.json"
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return OvernightFieldRunState(**data)
