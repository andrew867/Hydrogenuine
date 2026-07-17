"""Extended dry autonomy checkpoint — local only."""

from __future__ import annotations

import hashlib
import json
import os
import uuid
from pathlib import Path

from hg_runtime.agent_turn_engine.turn_storage import journal_path, receipts_dir
from hg_runtime.agent_zero_state.hashing import hash_record, verify_record_hash
from hg_runtime.agent_zero_state.replay import replay_from_run, verify_replay_deterministic
from hg_runtime.agent_zero_state.state import create_agent_state
from hg_runtime.agent_zero_state.turn_journal import TurnJournal
from hg_runtime.extended_dry_autonomy.errors import ExtendedDryAutonomyCheckpointError
from hg_runtime.extended_dry_autonomy.schema import ExtendedDryAutonomyCheckpoint, now_iso
from hg_runtime.extended_dry_autonomy.storage import checkpoint_dir, run_dir, write_json


def _journal_head_hash(run_id: str, *, turn_base: Path) -> str:
    jpath = journal_path(run_id, base=turn_base)
    if not jpath.is_file():
        return hash_record({"empty": True})
    entries = TurnJournal(jpath).read_all()
    if not entries:
        return hash_record({"empty": True})
    return hash_record(entries[-1])


def _review_queue_hash(run_id: str, *, turn_base: Path) -> str:
    from hg_runtime.dry_soak.resource_watchdog import collect_resource_snapshot

    snap = collect_resource_snapshot(
        run_id=run_id,
        turn_index=0,
        turn_duration_seconds=0.0,
        turn_base=turn_base,
        dry_soak_root=turn_base.parent,
    )
    return hash_record({"review_queue_count": snap.review_queue_count})


def _artifact_manifest_hash(run_id: str, *, turn_base: Path) -> str:
    from hg_runtime.dry_soak.resource_watchdog import collect_resource_snapshot

    snap = collect_resource_snapshot(
        run_id=run_id,
        turn_index=0,
        turn_duration_seconds=0.0,
        turn_base=turn_base,
        dry_soak_root=turn_base.parent,
    )
    return hash_record({"artifact_count": snap.artifact_count})


def _state_hash(run_id: str, iteration_index: int, *, run_dir: Path) -> str:
    state_path = run_dir / "state.json"
    payload = json.loads(state_path.read_text(encoding="utf-8")) if state_path.is_file() else {}
    return hash_record({"run_id": run_id, "iteration_index": iteration_index, "state": payload})


def write_checkpoint(
    *,
    run_id: str,
    iteration_index: int,
    turn_result_ref: str | None,
    heartbeat_hash: str,
    boot_anchor_ref: str | None = None,
    extended_base: Path | None = None,
    turn_base: Path | None = None,
) -> ExtendedDryAutonomyCheckpoint:
    tbase = turn_base or Path(os.environ.get("HG_AGENT_TURN_BASE", ""))
    if not tbase:
        from hg_runtime.agent_turn_engine.turn_storage import turns_root

        tbase = turns_root()
    rdir = checkpoint_dir(run_id, base=extended_base).parent
    cp = ExtendedDryAutonomyCheckpoint(
        checkpoint_id=f"ckpt-{uuid.uuid4().hex[:12]}",
        run_id=run_id,
        iteration_index=iteration_index,
        turn_result_ref=turn_result_ref,
        state_hash=_state_hash(run_id, iteration_index, run_dir=rdir),
        journal_head_hash=_journal_head_hash(run_id, turn_base=tbase),
        review_queue_hash=_review_queue_hash(run_id, turn_base=tbase),
        artifact_manifest_hash=_artifact_manifest_hash(run_id, turn_base=tbase),
        heartbeat_hash=heartbeat_hash,
        boot_anchor_ref=boot_anchor_ref,
        created_at=now_iso(),
    ).with_hash()
    path = checkpoint_dir(run_id, base=extended_base) / f"{cp.checkpoint_id}.json"
    write_json(path, cp.to_payload())
    write_json(rdir / "latest_checkpoint.json", cp.to_payload())
    return cp


def load_checkpoint(
    run_id: str,
    checkpoint_id: str | None = None,
    *,
    extended_base: Path | None = None,
) -> ExtendedDryAutonomyCheckpoint | None:
    if checkpoint_id:
        path = checkpoint_dir(run_id, base=extended_base) / f"{checkpoint_id}.json"
    else:
        path = run_dir(run_id, base=extended_base) / "latest_checkpoint.json"
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return ExtendedDryAutonomyCheckpoint(
        checkpoint_id=data["checkpoint_id"],
        run_id=data["run_id"],
        iteration_index=int(data["iteration_index"]),
        turn_result_ref=data.get("turn_result_ref"),
        state_hash=data["state_hash"],
        journal_head_hash=data["journal_head_hash"],
        review_queue_hash=data["review_queue_hash"],
        artifact_manifest_hash=data["artifact_manifest_hash"],
        heartbeat_hash=data["heartbeat_hash"],
        boot_anchor_ref=data.get("boot_anchor_ref"),
        last_shutdown_anchor_ref=data.get("last_shutdown_anchor_ref"),
        created_at=data.get("created_at", ""),
        hash=data.get("hash", ""),
    )


def verify_checkpoint(
    checkpoint: ExtendedDryAutonomyCheckpoint,
    *,
    extended_base: Path | None = None,
    turn_base: Path | None = None,
    agent_id: str = "zero",
) -> tuple[bool, str]:
    body = {k: v for k, v in checkpoint.to_payload().items() if k != "hash"}
    if not verify_record_hash(body, checkpoint.hash):
        return False, "RED_EXTENDED_DRY_AUTONOMY_CHECKPOINT_FAILURE:hash_mismatch"

    tbase = turn_base or Path(os.environ.get("HG_AGENT_TURN_BASE", ""))
    if not tbase:
        from hg_runtime.agent_turn_engine.turn_storage import turns_root

        tbase = turns_root()
    rdir = run_dir(checkpoint.run_id, base=extended_base)
    if checkpoint.state_hash != _state_hash(checkpoint.run_id, checkpoint.iteration_index, run_dir=rdir):
        return False, "RED_EXTENDED_DRY_AUTONOMY_CHECKPOINT_FAILURE:state_hash_mismatch"
    if checkpoint.journal_head_hash != _journal_head_hash(checkpoint.run_id, turn_base=tbase):
        return False, "RED_EXTENDED_DRY_AUTONOMY_CHECKPOINT_FAILURE:journal_hash_mismatch"

    if checkpoint.iteration_index > 0:
        journal = journal_path(checkpoint.run_id, base=tbase)
        if not journal.is_file():
            return False, "RED_EXTENDED_DRY_AUTONOMY_CHECKPOINT_FAILURE:journal_missing"
        entries = TurnJournal(journal).read_all()
        if len(entries) < checkpoint.iteration_index:
            return False, "RED_EXTENDED_DRY_AUTONOMY_CHECKPOINT_FAILURE:journal_count"
        receipt_files = list(receipts_dir(checkpoint.run_id, base=tbase).glob("*.json")) if receipts_dir(checkpoint.run_id, base=tbase).is_dir() else []
        if len(receipt_files) < checkpoint.iteration_index:
            return False, "RED_EXTENDED_DRY_AUTONOMY_CHECKPOINT_FAILURE:receipt_gap"
        _, initial = create_agent_state(agent_id=agent_id, run_id=checkpoint.run_id, runtime_mode="local_dev")
        replayed = replay_from_run(checkpoint.run_id, initial, base=tbase)
        if not verify_replay_deterministic(initial, TurnJournal(journal), replayed):
            return False, "RED_EXTENDED_DRY_AUTONOMY_CHECKPOINT_FAILURE:replay_mismatch"
    return True, "GREEN_CHECKPOINT_VERIFIED"


def resume_from_checkpoint(
    checkpoint: ExtendedDryAutonomyCheckpoint,
    *,
    extended_base: Path | None = None,
    turn_base: Path | None = None,
    agent_id: str = "zero",
) -> dict:
    ok, reason = verify_checkpoint(checkpoint, extended_base=extended_base, turn_base=turn_base, agent_id=agent_id)
    if not ok:
        raise ExtendedDryAutonomyCheckpointError(reason)
    receipt = {
        "schema": "extended-dry-autonomy-resume-receipt",
        "run_id": checkpoint.run_id,
        "checkpoint_id": checkpoint.checkpoint_id,
        "iteration_index": checkpoint.iteration_index,
        "verified_at": now_iso(),
        "verdict": reason,
    }
    write_json(run_dir(checkpoint.run_id, base=extended_base) / "resume_receipt.json", receipt)
    return receipt


__all__ = ["load_checkpoint", "resume_from_checkpoint", "verify_checkpoint", "write_checkpoint"]
