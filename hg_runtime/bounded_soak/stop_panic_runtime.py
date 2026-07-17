"""STOP vs PANIC runtime semantics for bounded soak."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

WORKSPACE = Path(__file__).resolve().parents[2]


@dataclass
class StopPanicRuntimeState:
    stop_active: bool = False
    panic_active: bool = False
    require_operator_review: bool = False

    def blocks_new_supervisor(self) -> bool:
        return self.stop_active or self.panic_active

    def blocks_approval(self) -> bool:
        return self.panic_active or self.require_operator_review

    def blocks_side_effects(self) -> bool:
        return self.stop_active or self.panic_active


def stop_panic_state(workspace: Path | None = None) -> StopPanicRuntimeState:
    ws = workspace or WORKSPACE
    soak = ws / ".hg-local" / "soak"
    stop = (soak / "STOP").is_file()
    panic = (soak / "PANIC").is_file()
    require_review = False
    ctrl = soak / "control_state.json"
    if ctrl.is_file():
        try:
            data = json.loads(ctrl.read_text(encoding="utf-8"))
            require_review = bool(data.get("require_operator_review"))
        except (OSError, json.JSONDecodeError):
            pass
    return StopPanicRuntimeState(stop_active=stop, panic_active=panic, require_operator_review=require_review)


def _append_receipt(ws: Path, payload: dict[str, Any]) -> str:
    path = ws / ".hg-local" / "soak" / "stop_panic_receipts.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    rid = payload.get("receipt_id", f"spr-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}")
    payload.setdefault("receipt_id", rid)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, sort_keys=True) + "\n")
    return rid


def write_stop_receipt(
    workspace: Path | None = None,
    *,
    run_dir: Path | None = None,
    operator_ref: str = "local-operator",
) -> str:
    ws = workspace or WORKSPACE
    payload = {
        "schema": "soak-stop-receipt",
        "kind": "STOP",
        "semantics": "graceful_stop_no_new_side_effects",
        "operator_ref": operator_ref,
        "run_dir": str(run_dir) if run_dir else None,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "advisory_only": True,
        "permission_granted": False,
        "authority_created": False,
    }
    return _append_receipt(ws, payload)


def write_panic_receipt(
    workspace: Path | None = None,
    *,
    run_dir: Path | None = None,
    operator_ref: str = "local-operator",
) -> str:
    ws = workspace or WORKSPACE
    soak = ws / ".hg-local" / "soak"
    soak.mkdir(parents=True, exist_ok=True)
    (soak / "PANIC").write_text("1\n", encoding="utf-8")
    ctrl = {"require_operator_review": True, "panic_at": datetime.now(timezone.utc).isoformat()}
    (soak / "control_state.json").write_text(json.dumps(ctrl, indent=2) + "\n", encoding="utf-8")
    payload = {
        "schema": "soak-panic-receipt",
        "kind": "PANIC",
        "semantics": "immediate_halt_blocks_approval_until_reset",
        "operator_ref": operator_ref,
        "run_dir": str(run_dir) if run_dir else None,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "require_operator_review": True,
        "advisory_only": True,
        "permission_granted": False,
        "authority_created": False,
    }
    return _append_receipt(ws, payload)


def may_start_supervisor(workspace: Path | None = None) -> tuple[bool, str]:
    sp = stop_panic_state(workspace)
    if sp.panic_active:
        return False, "RED_STOP_DOES_NOT_BLOCK_RESTART:panic_active"
    if sp.stop_active:
        return False, "RED_STOP_DOES_NOT_BLOCK_RESTART:stop_active"
    return True, "ok"


def operator_semantics() -> dict[str, str]:
    return {
        "STOP": "Graceful stop: no new publish or side effects; finish safe unit if allowed; receipt written.",
        "PANIC": "Immediate halt: block approvals and execution; require operator review before restart.",
    }


__all__ = [
    "StopPanicRuntimeState",
    "may_start_supervisor",
    "operator_semantics",
    "stop_panic_state",
    "write_panic_receipt",
    "write_stop_receipt",
]
