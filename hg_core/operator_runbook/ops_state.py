"""Runtime ops state for panic/safe-mode visibility (CT-15 RUN)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def ops_state_path(workspace: Path, *, relative: str = "runtime/ops/ops_state_v1.json") -> Path:
    return workspace / relative


@dataclass
class OpsState:
    panic_active: bool = False
    safe_mode: bool = False
    queues_frozen: bool = False
    oea_real_disabled: bool = False
    ter_disabled: bool = False
    max_auto_disabled: bool = False
    live_cognition_revoked: bool = False
    lockdown_active: bool = False
    runtime_stopped: bool = False
    last_replay_ok: bool | None = None
    last_replay_at: str | None = None
    updated_at: str | None = None
    last_procedure: str | None = None
    last_operator_id: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema": "ops_state_v1",
            "panic_active": self.panic_active,
            "safe_mode": self.safe_mode,
            "queues_frozen": self.queues_frozen,
            "oea_real_disabled": self.oea_real_disabled,
            "ter_disabled": self.ter_disabled,
            "max_auto_disabled": self.max_auto_disabled,
            "live_cognition_revoked": self.live_cognition_revoked,
            "lockdown_active": self.lockdown_active,
            "runtime_stopped": self.runtime_stopped,
            "last_replay_ok": self.last_replay_ok,
            "last_replay_at": self.last_replay_at,
            "updated_at": self.updated_at,
            "last_procedure": self.last_procedure,
            "last_operator_id": self.last_operator_id,
        }

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> OpsState:
        return cls(
            panic_active=bool(payload.get("panic_active", False)),
            safe_mode=bool(payload.get("safe_mode", False)),
            queues_frozen=bool(payload.get("queues_frozen", False)),
            oea_real_disabled=bool(payload.get("oea_real_disabled", False)),
            ter_disabled=bool(payload.get("ter_disabled", False)),
            max_auto_disabled=bool(payload.get("max_auto_disabled", False)),
            live_cognition_revoked=bool(payload.get("live_cognition_revoked", False)),
            lockdown_active=bool(payload.get("lockdown_active", False)),
            runtime_stopped=bool(payload.get("runtime_stopped", False)),
            last_replay_ok=payload.get("last_replay_ok"),
            last_replay_at=payload.get("last_replay_at"),
            updated_at=payload.get("updated_at"),
            last_procedure=payload.get("last_procedure"),
            last_operator_id=payload.get("last_operator_id"),
        )


def load_ops_state(workspace: Path, *, relative: str = "runtime/ops/ops_state_v1.json") -> OpsState:
    path = ops_state_path(workspace, relative=relative)
    if not path.exists():
        return OpsState()
    payload = json.loads(path.read_text(encoding="utf-8"))
    return OpsState.from_payload(payload)


def save_ops_state(
    workspace: Path,
    state: OpsState,
    *,
    relative: str = "runtime/ops/ops_state_v1.json",
    procedure_id: str | None = None,
    operator_id: str | None = None,
) -> OpsState:
    state.updated_at = _utc_now()
    if procedure_id is not None:
        state.last_procedure = procedure_id
    if operator_id is not None:
        state.last_operator_id = operator_id
    path = ops_state_path(workspace, relative=relative)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state.to_payload(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return state


def status_summary(state: OpsState) -> dict[str, Any]:
    mode = "normal"
    if state.lockdown_active:
        mode = "lockdown"
    elif state.safe_mode:
        mode = "safe_mode"
    elif state.panic_active:
        mode = "panic"
    return {
        "mode": mode,
        "panic_active": state.panic_active,
        "safe_mode": state.safe_mode,
        "queues_frozen": state.queues_frozen,
        "oea_real_disabled": state.oea_real_disabled,
        "ter_disabled": state.ter_disabled,
        "live_cognition_revoked": state.live_cognition_revoked,
        "lockdown_active": state.lockdown_active,
        "runtime_stopped": state.runtime_stopped,
        "last_replay_ok": state.last_replay_ok,
    }


__all__ = ["OpsState", "load_ops_state", "ops_state_path", "save_ops_state", "status_summary"]
