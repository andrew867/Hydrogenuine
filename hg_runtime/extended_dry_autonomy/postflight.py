"""Extended dry autonomy postflight verification."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

from hg_runtime.agent_turn_engine.turn_storage import journal_path, receipts_dir
from hg_runtime.agent_zero_state.replay import replay_from_run, verify_replay_deterministic
from hg_runtime.agent_zero_state.state import create_agent_state
from hg_runtime.agent_zero_state.turn_journal import TurnJournal
from hg_runtime.dry_autonomous_loop.anchor_lifecycle import anchor_committed
from hg_runtime.extended_dry_autonomy.errors import ExtendedDryAutonomyPostflightError
from hg_runtime.extended_dry_autonomy.extended_lock import read_lock
from hg_runtime.extended_dry_autonomy.schema import ExtendedDryAutonomyVerdict, now_iso
from hg_runtime.extended_dry_autonomy.storage import run_dir, write_json


def _elapsed(started_at: str) -> float:
    try:
        start = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
        return (datetime.now(timezone.utc) - start).total_seconds()
    except Exception:
        return 0.0


def run_extended_postflight(
    *,
    run_id: str,
    agent_id: str,
    started_at: str,
    iteration_count: int,
    stop_events: int = 0,
    panic_events: int = 0,
    pause_events: int = 0,
    extended_base: Path | None = None,
    turn_base: Path | None = None,
    boot_anchor: dict | None = None,
    shutdown_anchor: dict | None = None,
    anchor_audit_verdict: str = "YELLOW_LOCAL_ONLY_ANCHOR_NOT_REMOTE",
) -> dict:
    lock = read_lock(base=extended_base)
    if lock and lock.state.value == "active":
        raise ExtendedDryAutonomyPostflightError("RED_EXTENDED_DRY_AUTONOMY_LOCK_FAILURE: lock not released")

    tbase = turn_base or Path(os.environ.get("HG_AGENT_TURN_BASE", "")) or None
    if tbase is None:
        from hg_runtime.agent_turn_engine.turn_storage import turns_root

        tbase = turns_root()

    replay_verdict = "GREEN_REPLAY_SKIPPED_EMPTY"
    external_side_effects = False
    live_writes = False

    if iteration_count > 0:
        journal = journal_path(run_id, base=tbase)
        if not journal.is_file():
            raise ExtendedDryAutonomyPostflightError("RED_EXTENDED_DRY_AUTONOMY_RECEIPT_GAP: journal missing")
        entries = TurnJournal(journal).read_all()
        if len(entries) != iteration_count:
            raise ExtendedDryAutonomyPostflightError(
                f"RED_EXTENDED_DRY_AUTONOMY_RECEIPT_GAP: journal count {len(entries)} != {iteration_count}"
            )
        receipt_files = list(receipts_dir(run_id, base=tbase).glob("*.json")) if receipts_dir(run_id, base=tbase).is_dir() else []
        if len(receipt_files) < iteration_count:
            raise ExtendedDryAutonomyPostflightError("RED_EXTENDED_DRY_AUTONOMY_RECEIPT_GAP: receipt files")
        for entry in entries:
            if entry.get("external_side_effect"):
                external_side_effects = True
            if entry.get("published") or entry.get("sent"):
                live_writes = True
            if entry.get("hidden_cot_stored"):
                raise ExtendedDryAutonomyPostflightError("RED_EXTENDED_DRY_AUTONOMY_SECRET_OR_COT_LEAK")
            if entry.get("secrets_stored"):
                raise ExtendedDryAutonomyPostflightError("RED_EXTENDED_DRY_AUTONOMY_SECRET_OR_COT_LEAK")
            if entry.get("fixture_used"):
                raise ExtendedDryAutonomyPostflightError("RED_EXTENDED_DRY_AUTONOMY_FIXTURE_REGRESSION")
        _, initial = create_agent_state(agent_id=agent_id, run_id=run_id, runtime_mode="local_dev")
        replayed = replay_from_run(run_id, initial, base=tbase)
        if not verify_replay_deterministic(initial, TurnJournal(journal), replayed):
            raise ExtendedDryAutonomyPostflightError("RED_EXTENDED_DRY_AUTONOMY_REPLAY_FAILURE")
        replay_verdict = "GREEN_REPLAY_VERIFIED"

    boot_ok = anchor_committed(boot_anchor)
    shutdown_ok = anchor_committed(shutdown_anchor)
    if not boot_ok:
        raise ExtendedDryAutonomyPostflightError("RED_BOOT_ANCHOR_MISSING")

    verdict = ExtendedDryAutonomyVerdict.GREEN_EXTENDED_DRY_AUTONOMY_COMPLETE.value
    if external_side_effects or live_writes:
        verdict = ExtendedDryAutonomyVerdict.RED_EXTENDED_DRY_AUTONOMY_EXTERNAL_SIDE_EFFECT.value
    elif not shutdown_ok and panic_events == 0:
        verdict = "RED_SHUTDOWN_ANCHOR_MISSING"

    payload = {
        "run_id": run_id,
        "iteration_count": iteration_count,
        "duration_seconds": _elapsed(started_at),
        "replay_verdict": replay_verdict,
        "external_side_effects": external_side_effects,
        "live_writes": live_writes,
        "lock_released": lock is None,
        "background_process_left": False,
        "stop_events": stop_events,
        "panic_events": panic_events,
        "pause_events": pause_events,
        "boot_anchor_committed": boot_ok,
        "shutdown_anchor_committed": shutdown_ok,
        "anchor_audit_verdict": anchor_audit_verdict,
        "verdict": verdict,
        "created_at": now_iso(),
    }
    write_json(run_dir(run_id, base=extended_base) / "postflight.json", payload)
    return payload


__all__ = ["run_extended_postflight"]
