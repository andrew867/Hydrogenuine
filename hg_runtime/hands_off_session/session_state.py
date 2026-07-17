"""Hands-off session state."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from hg_core.policy_safety.hashing import compute_record_hash
from hg_runtime.hands_off_session.schema import HandsOffSessionStatus, session_dir, now_iso


@dataclass
class HandsOffSessionState:
    session_id: str
    pid: int
    status: str
    started_at: str
    turn_count: int = 0
    selected_task_count: int = 0
    idle_count: int = 0
    stop_requested: bool = False
    panic_requested: bool = False
    failure_budget_status: str = "ok"
    resource_budget_status: str = "ok"
    external_side_effect_count: int = 0
    stopped_at: str | None = None
    last_turn_ref: str | None = None
    last_task_selection_ref: str | None = None
    last_broker_decision_ref: str | None = None
    last_heartbeat_ref: str | None = None
    last_governed_work_receipt_ref: str | None = None
    hash: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "pid": self.pid,
            "status": self.status,
            "started_at": self.started_at,
            "stopped_at": self.stopped_at,
            "turn_count": self.turn_count,
            "selected_task_count": self.selected_task_count,
            "idle_count": self.idle_count,
            "last_turn_ref": self.last_turn_ref,
            "last_task_selection_ref": self.last_task_selection_ref,
            "last_broker_decision_ref": self.last_broker_decision_ref,
            "last_heartbeat_ref": self.last_heartbeat_ref,
            "last_governed_work_receipt_ref": self.last_governed_work_receipt_ref,
            "stop_requested": self.stop_requested,
            "panic_requested": self.panic_requested,
            "failure_budget_status": self.failure_budget_status,
            "resource_budget_status": self.resource_budget_status,
            "external_side_effect_count": self.external_side_effect_count,
            "hash": self.hash,
        }

    def with_hash(self) -> HandsOffSessionState:
        body = {k: v for k, v in self.to_payload().items() if k != "hash"}
        return HandsOffSessionState(**{**self.__dict__, "hash": compute_record_hash(body)})


def state_path(session_id: str, *, base: Path | None = None) -> Path:
    return session_dir(session_id, base=base) / "state.json"


def persist_state(state: HandsOffSessionState, *, base: Path | None = None) -> Path:
    path = state_path(state.session_id, base=base)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state.to_payload(), indent=2) + "\n", encoding="utf-8")
    status_path = path.parent / "STATUS.json"
    status_path.write_text(json.dumps(state.to_payload(), indent=2) + "\n", encoding="utf-8")
    return path


def load_state(session_id: str, *, base: Path | None = None) -> HandsOffSessionState | None:
    path = state_path(session_id, base=base)
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return HandsOffSessionState(
        session_id=data["session_id"],
        pid=int(data["pid"]),
        status=data["status"],
        started_at=data["started_at"],
        stopped_at=data.get("stopped_at"),
        turn_count=int(data.get("turn_count", 0)),
        selected_task_count=int(data.get("selected_task_count", 0)),
        idle_count=int(data.get("idle_count", 0)),
        last_turn_ref=data.get("last_turn_ref"),
        last_task_selection_ref=data.get("last_task_selection_ref"),
        last_broker_decision_ref=data.get("last_broker_decision_ref"),
        last_heartbeat_ref=data.get("last_heartbeat_ref"),
        last_governed_work_receipt_ref=data.get("last_governed_work_receipt_ref"),
        stop_requested=bool(data.get("stop_requested")),
        panic_requested=bool(data.get("panic_requested")),
        failure_budget_status=data.get("failure_budget_status", "ok"),
        resource_budget_status=data.get("resource_budget_status", "ok"),
        external_side_effect_count=int(data.get("external_side_effect_count", 0)),
        hash=data.get("hash"),
    )
