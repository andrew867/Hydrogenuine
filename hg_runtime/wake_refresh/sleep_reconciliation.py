"""Sleep state persistence and reconciliation."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hg_runtime.wake_refresh.schema import (
    FROZEN_FALSE,
    PreviousSleepState,
    SleepReconciliation,
    UnfinishedWorkClassification,
    UnfinishedWorkItem,
)

WORKSPACE = Path(__file__).resolve().parents[2]
WRR_DIR = WORKSPACE / ".hg-local" / "wake_refresh"
SLEEP_STATE_PATH = WRR_DIR / "last_sleep_state.json"


def sleep_state_path(workspace: Path | None = None) -> Path:
    ws = workspace or WORKSPACE
    return ws / ".hg-local" / "wake_refresh" / "last_sleep_state.json"


def write_sleep_state(state: dict[str, Any], *, workspace: Path | None = None) -> Path:
    path = sleep_state_path(workspace)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {**state, **FROZEN_FALSE}
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return path


def read_sleep_state(*, workspace: Path | None = None) -> dict[str, Any] | None:
    path = sleep_state_path(workspace)
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def build_sleep_state_from_shutdown(
    *,
    run_id: str,
    epoch_id: str | None = None,
    epoch_lock_id: str | None = None,
    shutdown_clean: bool = True,
    pending_tasks: list[str] | None = None,
    open_tool_requests: list[str] | None = None,
    stop_receipt_ref: str | None = None,
    panic_state: bool = False,
) -> dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    return {
        "schema": "agent-zero-sleep-state",
        "run_id": run_id,
        "epoch_id": epoch_id,
        "epoch_lock_id": epoch_lock_id,
        "shutdown_started_at": now,
        "shutdown_completed_at": now if shutdown_clean else None,
        "shutdown_clean": shutdown_clean,
        "pending_tasks": pending_tasks or [],
        "open_tool_requests": open_tool_requests or [],
        "draft_status": "none",
        "provider_status": "stopped",
        "browser_status": "closed",
        "audio_status": "idle",
        "memory_write_requests": [],
        "proof_flush_status": "preserved",
        "stop_receipt_ref": stop_receipt_ref,
        "panic_state": panic_state,
        **FROZEN_FALSE,
    }


def reconcile_on_wake(state: dict[str, Any] | None) -> SleepReconciliation:
    if state is None:
        return SleepReconciliation(
            previous_state=PreviousSleepState.ABSENT,
            sleep_state=None,
            stop_receipt_verified=False,
        )

    clean = bool(state.get("shutdown_clean"))
    prev = PreviousSleepState.CLEAN if clean else PreviousSleepState.UNCLEAN
    items: list[UnfinishedWorkItem] = []

    for i, task in enumerate(state.get("pending_tasks") or []):
        items.append(
            UnfinishedWorkItem(
                item_id=f"task-{i}",
                description=str(task),
                classification=UnfinishedWorkClassification.INTERRUPTED_NEEDS_REVIEW
                if not clean
                else UnfinishedWorkClassification.SAFE_TO_RETRY,
            )
        )
    for i, req in enumerate(state.get("open_tool_requests") or []):
        items.append(
            UnfinishedWorkItem(
                item_id=f"tool-{i}",
                description=str(req),
                classification=UnfinishedWorkClassification.UNKNOWN_NEEDS_REVIEW,
            )
        )
    if state.get("panic_state"):
        items.append(
            UnfinishedWorkItem(
                item_id="panic-0",
                description="previous run ended in panic",
                classification=UnfinishedWorkClassification.BLOCKING_WAKE,
            )
        )

    return SleepReconciliation(
        previous_state=prev,
        sleep_state=state,
        unfinished_items=items,
        stop_receipt_verified=bool(state.get("stop_receipt_ref")),
    )


__all__ = [
    "SLEEP_STATE_PATH",
    "WRR_DIR",
    "build_sleep_state_from_shutdown",
    "read_sleep_state",
    "reconcile_on_wake",
    "sleep_state_path",
    "write_sleep_state",
]
