"""Postflight verification for supervised rehearsal."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from hg_runtime.agent_turn_engine.turn_storage import journal_path, receipts_dir, run_dir as turn_run_dir
from hg_runtime.agent_zero_state.replay import replay_from_run, verify_replay_deterministic
from hg_runtime.agent_zero_state.state import create_agent_state
from hg_runtime.agent_zero_state.turn_journal import TurnJournal
from hg_runtime.output_artifacts.artifact_store import ArtifactStore
from hg_runtime.supervised_rehearsal.errors import PostflightError
from hg_runtime.supervised_rehearsal.rehearsal_store import RehearsalStore, current_lock_path
from hg_runtime.supervised_rehearsal.run_lock import read_lock
from hg_runtime.supervised_rehearsal.schema import PostflightSummary, SupervisedRehearsalVerdict, now_iso


def _turn_base(run_id: str, *, turn_base: Path | None = None) -> Path:
    return turn_base or turn_run_dir(run_id).parent


def run_postflight(
    *,
    run_id: str,
    agent_id: str,
    started_at: str,
    turn_count: int,
    stop_events: int = 0,
    panic_events: int = 0,
    rehearsal_base: Path | None = None,
    turn_base: Path | None = None,
) -> PostflightSummary:
    store = RehearsalStore(run_id, base=rehearsal_base)
    tbase = _turn_base(run_id, turn_base=turn_base)
    tdir = tbase / run_id

    started = time.time()
    try:
        from datetime import datetime, timezone

        start_ts = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
        duration = (datetime.now(timezone.utc) - start_ts).total_seconds()
    except Exception:
        duration = 0.0

    lock = read_lock(base=rehearsal_base)
    if lock and lock.state.value == "active":
        raise PostflightError("RED_REHEARSAL_LOCK_MISSING: lock not released")

    journal = journal_path(run_id, base=tbase)
    if turn_count == 0:
        if lock and lock.state.value == "active":
            raise PostflightError("RED_REHEARSAL_LOCK_MISSING: lock not released")
        summary = PostflightSummary(
            run_id=run_id,
            turn_count=0,
            duration_seconds=duration,
            turn_receipts=[],
            journal_ref=str(journal) if journal.is_file() else None,
            replay_verdict="GREEN_REPLAY_SKIPPED_EMPTY",
            artifact_count=0,
            review_candidate_count=0,
            stop_events=stop_events,
            panic_events=panic_events,
            external_side_effects=False,
            live_writes=False,
            verdict=SupervisedRehearsalVerdict.YELLOW_REHEARSAL_STOPPED_BY_OPERATOR.value if stop_events or panic_events else SupervisedRehearsalVerdict.GREEN_SUPERVISED_REHEARSAL_COMPLETE.value,
            created_at=now_iso(),
        ).with_hash()
        store.store_postflight(summary)
        return summary

    if not journal.is_file():
        raise PostflightError("RED_REHEARSAL_RECEIPT_MISSING: journal missing")

    j = TurnJournal(journal)
    entries = j.read_all()
    if len(entries) != turn_count:
        raise PostflightError(f"RED_REHEARSAL_RECEIPT_MISSING: journal count {len(entries)} != {turn_count}")

    receipt_ids: list[str] = []
    external_side_effects = False
    live_writes = False
    for entry in entries:
        rid = entry.get("receipt_id")
        if not rid:
            raise PostflightError("RED_REHEARSAL_RECEIPT_MISSING")
        receipt_ids.append(rid)
        if entry.get("external_side_effect"):
            external_side_effects = True
        if entry.get("published") or entry.get("sent"):
            live_writes = True
        if entry.get("hidden_cot_stored"):
            raise PostflightError("RED_HIDDEN_COT_STORED")
        if entry.get("secrets_stored"):
            raise PostflightError("RED_SECRET_STORED")
        if entry.get("fixture_used"):
            raise PostflightError("RED_FIXTURE_RUNTIME_TRUTH")

    receipt_files = list(receipts_dir(run_id, base=tbase).glob("*.json")) if receipts_dir(run_id, base=tbase).is_dir() else []
    if len(receipt_files) < turn_count:
        raise PostflightError("RED_REHEARSAL_RECEIPT_MISSING: receipt files")

    _, initial = create_agent_state(agent_id=agent_id, run_id=run_id, runtime_mode="local_dev")
    replayed = replay_from_run(run_id, initial, base=tbase)
    if not verify_replay_deterministic(initial, j, replayed):
        raise PostflightError("RED_REHEARSAL_REPLAY_FAILURE")

    artifact_count = 0
    review_count = 0
    try:
        astore = ArtifactStore(run_id, base=tbase.parent if turn_base else None)
        if astore.manifest_path.is_file():
            manifest = astore.read_manifest()
            artifact_count = sum(1 for m in manifest if m.get("kind") == "artifact")
            review_count = sum(1 for m in manifest if m.get("kind") == "review_candidate")
    except Exception:
        artifact_count = 0
        review_count = 0

    verdict = SupervisedRehearsalVerdict.GREEN_SUPERVISED_REHEARSAL_COMPLETE.value
    if external_side_effects:
        verdict = SupervisedRehearsalVerdict.RED_REHEARSAL_EXTERNAL_SIDE_EFFECT.value
    if live_writes:
        verdict = SupervisedRehearsalVerdict.RED_REHEARSAL_EXTERNAL_SIDE_EFFECT.value

    summary = PostflightSummary(
        run_id=run_id,
        turn_count=turn_count,
        duration_seconds=duration,
        turn_receipts=receipt_ids,
        journal_ref=str(journal),
        replay_verdict="GREEN_REPLAY_OK",
        artifact_count=artifact_count,
        review_candidate_count=review_count,
        stop_events=stop_events,
        panic_events=panic_events,
        external_side_effects=external_side_effects,
        live_writes=live_writes,
        verdict=verdict,
        created_at=now_iso(),
    ).with_hash()
    store.store_postflight(summary)
    return summary


__all__ = ["run_postflight"]
