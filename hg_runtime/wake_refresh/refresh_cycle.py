"""Wake refresh cycle orchestration."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from hg_runtime.wake_refresh.boot_hygiene import WORKSPACE
from hg_runtime.wake_refresh.receipts import new_wake_receipt
from hg_runtime.wake_refresh.schema import (
    PreviousSleepState,
    WakeReadiness,
    WakeReadinessContext,
    WakeRefreshCycle,
)
from hg_runtime.wake_refresh.sleep_reconciliation import read_sleep_state, reconcile_on_wake
from hg_runtime.wake_refresh.transient_cleanup import scan_transient
from hg_runtime.wake_refresh.unfinished_work import classify_unfinished, count_requires_review
from hg_runtime.wake_refresh.waste_elimination import apply_cleanup
from hg_runtime.external_witness_journal.lifecycle import append_wake_refresh_complete, append_wake_refresh_start

READINESS_PATH = WORKSPACE / ".hg-local" / "wake_refresh" / "wake_readiness_context.json"


@dataclass
class WakeRefreshConfig:
    dry_run: bool = True
    max_seconds: float = 60.0
    max_cleanup_items: int = 50
    panic_file: Path | None = None


def run_wake_refresh_cycle(
    *,
    workspace: Path | None = None,
    config: WakeRefreshConfig | None = None,
    epoch_id: str | None = None,
    chrono_lock: dict[str, Any] | None = None,
) -> WakeRefreshCycle:
    ws = workspace or WORKSPACE
    cfg = config or WakeRefreshConfig()
    started = time.monotonic()
    epoch_id = epoch_id or (chrono_lock or {}).get("epoch_id")

    try:
        append_wake_refresh_start(epoch_id=epoch_id, dry_run=cfg.dry_run)
    except (OSError, ValueError, TypeError):
        pass

    if cfg.panic_file and cfg.panic_file.is_file():
        cycle = _build_cycle(
            verdict="RED_WAKE_REFRESH_MISSING_RECEIPT",
            reconciliation=reconcile_on_wake(read_sleep_state(workspace=ws)),
            hygiene=scan_transient(workspace=ws),
            waste_receipts=[],
            cleanup_applied=False,
            epoch_id=epoch_id,
        )
        cycle.wake_receipt = new_wake_receipt("RED_WAKE_REFRESH_MISSING_RECEIPT", cleanup_applied=False, waste_count=0, epoch_id=epoch_id)
        return cycle

    sleep_state = read_sleep_state(workspace=ws)
    reconciliation = reconcile_on_wake(sleep_state)
    hygiene = scan_transient(workspace=ws)
    unfinished = classify_unfinished(reconciliation)

    if time.monotonic() - started > cfg.max_seconds:
        return _build_cycle(
            verdict="RED_WAKE_REFRESH_UNBOUNDED_CLEANUP",
            reconciliation=reconciliation,
            hygiene=hygiene,
            waste_receipts=[],
            cleanup_applied=False,
            epoch_id=epoch_id,
            unfinished=unfinished,
        )

    waste_receipts: list = []
    failures: list[str] = []
    apply_cleanup_flag = not cfg.dry_run
    max_passes = 20 if apply_cleanup_flag else 1
    for _pass in range(max_passes):
        hygiene = scan_transient(workspace=ws)
        batch_receipts, batch_failures, hygiene, truncated = apply_cleanup(
            hygiene,
            apply=apply_cleanup_flag,
            workspace=ws,
            epoch_id=epoch_id,
            max_items=cfg.max_cleanup_items,
        )
        waste_receipts.extend(batch_receipts)
        failures.extend(batch_failures)
        if not apply_cleanup_flag or not truncated:
            break
        deleted = [r for r in batch_receipts if r.method not in ("dry_run",)]
        if not deleted:
            failures.append("RED_WAKE_REFRESH_UNBOUNDED_CLEANUP")
            break
    failures = list(dict.fromkeys(failures))

    verdict = "GREEN_WAKE_REFRESH_READY"
    warnings: list[str] = []

    if reconciliation.previous_state == PreviousSleepState.ABSENT:
        warnings.append("YELLOW_PREVIOUS_SLEEP_STATE_ABSENT")
        if verdict == "GREEN_WAKE_REFRESH_READY":
            verdict = "YELLOW_PREVIOUS_SLEEP_STATE_ABSENT"

    if reconciliation.previous_state == PreviousSleepState.UNCLEAN:
        warnings.append("YELLOW_WAKE_REFRESH_PARTIAL")
        if verdict.startswith("GREEN"):
            verdict = "YELLOW_WAKE_REFRESH_PARTIAL"

    if failures:
        if any("RED_WAKE_REFRESH_DELETED_PROOF" in f for f in failures):
            verdict = "RED_WAKE_REFRESH_DELETED_PROOF"
        elif any("UNBOUNDED" in f for f in failures):
            verdict = "RED_WAKE_REFRESH_UNBOUNDED_CLEANUP"
        elif any("STALE_LOCK" in f for f in failures):
            verdict = "RED_WAKE_REFRESH_STALE_LOCK_LEFTOVER"
        else:
            verdict = "YELLOW_WAKE_REFRESH_PARTIAL"

    if hygiene.stale_locks and not cfg.dry_run and verdict.startswith("GREEN"):
        # stale locks remain after apply
        remaining = detect_remaining_locks(hygiene, ws)
        if remaining:
            verdict = "RED_WAKE_REFRESH_STALE_LOCK_LEFTOVER"

    review_count = count_requires_review(unfinished)
    readiness_level = WakeReadiness.GREEN if verdict.startswith("GREEN") else (
        WakeReadiness.YELLOW if verdict.startswith("YELLOW") else WakeReadiness.RED
    )

    cycle = _build_cycle(
        verdict=verdict,
        reconciliation=reconciliation,
        hygiene=hygiene,
        waste_receipts=waste_receipts,
        cleanup_applied=not cfg.dry_run,
        epoch_id=epoch_id,
        unfinished=unfinished,
        review_count=review_count,
        readiness_level=readiness_level,
    )
    cycle.wake_receipt = new_wake_receipt(
        verdict,
        cleanup_applied=not cfg.dry_run,
        waste_count=len([r for r in waste_receipts if r.method != "dry_run"]),
        epoch_id=epoch_id,
    )
    try:
        append_wake_refresh_complete(verdict, epoch_id=epoch_id, dry_run=cfg.dry_run)
    except (OSError, ValueError, TypeError):
        pass
    return cycle


def detect_remaining_locks(hygiene, ws: Path) -> list:
    from hg_runtime.wake_refresh.stale_locks import detect_stale_locks
    return detect_stale_locks(workspace=ws)


def _build_cycle(
    *,
    verdict: str,
    reconciliation,
    hygiene,
    waste_receipts,
    cleanup_applied: bool,
    epoch_id: str | None,
    unfinished=None,
    review_count: int = 0,
    readiness_level: WakeReadiness = WakeReadiness.GREEN,
) -> WakeRefreshCycle:
    unfinished = unfinished or classify_unfinished(reconciliation)
    readiness = WakeReadinessContext(
        enabled=True,
        previous_sleep_state=reconciliation.previous_state,
        cleanup_applied=cleanup_applied,
        stale_locks_found=len(hygiene.stale_locks),
        unfinished_work_count=len(unfinished),
        unfinished_work_requires_review=review_count or count_requires_review(unfinished),
        waste_eliminated_count=len([r for r in waste_receipts if r.method not in ("dry_run",)]),
        wake_readiness=readiness_level,
    )
    return WakeRefreshCycle(
        reconciliation=reconciliation,
        hygiene=hygiene,
        waste_receipts=waste_receipts,
        wake_receipt=new_wake_receipt(verdict, cleanup_applied=cleanup_applied, waste_count=0, epoch_id=epoch_id),
        readiness=readiness,
        verdict=verdict,
    )


def write_readiness_context(cycle: WakeRefreshCycle, path: Path | None = None) -> Path:
    out = path or READINESS_PATH
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "wake_refresh": cycle.readiness.to_payload(),
        "verdict": cycle.verdict,
        "wake_receipt": cycle.wake_receipt.to_payload(),
        "waste_receipts": [r.to_payload() for r in cycle.waste_receipts],
    }
    out.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return out


def load_readiness_context(path: Path | None = None) -> dict[str, Any] | None:
    p = path or READINESS_PATH
    if not p.is_file():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


__all__ = ["READINESS_PATH", "WakeRefreshConfig", "load_readiness_context", "run_wake_refresh_cycle", "write_readiness_context"]
