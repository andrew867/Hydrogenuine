"""Replay validation for the WMBR-02 verification queue.

Replay recomputes task hashes and the queue hash and confirms they are
unchanged. Any mutation is rejected. Replay asserts no boundary flag flipped
true (no claim marked true/false, no belief promoted, no tool authorized).
"""

from __future__ import annotations

from hg_runtime.belief_verification_queue.schemas import (
    REPLAY_RECORD_SCHEMA,
    assert_neutral,
    neutral_flags,
)
from hg_runtime.memory_ledger.hash_chain import canonical_hash


def _recompute(obj: dict, hash_key: str) -> tuple[str, str]:
    copy = dict(obj)
    stored = copy.pop(hash_key, None)
    return stored, canonical_hash(copy)


def replay_queue(tasks: list[dict], manifest: dict) -> dict:
    failures: list[str] = []

    for task in tasks:
        stored, recomputed = _recompute(task, "task_hash")
        if stored != recomputed:
            failures.append(f"task_hash_mismatch:{task.get('task_id')}")

    expected_hashes = [t["task_hash"] for t in tasks]
    if expected_hashes != manifest.get("task_hashes", []):
        failures.append("task_hash_list_mismatch")

    stored_q, recomputed_q = _recompute(manifest, "queue_hash")
    if stored_q != recomputed_q:
        failures.append("queue_hash_mismatch")

    try:
        for task in tasks:
            assert_neutral(task)
        assert_neutral(manifest)
    except Exception as exc:  # noqa: BLE001 - boundary violation surfaced as failure
        failures.append(f"boundary_violation:{exc}")

    record = {
        "schema": REPLAY_RECORD_SCHEMA,
        "ok": not failures,
        "replay_preserves_queue_hash": not failures,
        "failures": failures,
        "queue_hash": stored_q,
        "task_count": len(tasks),
        **neutral_flags(),
    }
    record["replay_hash"] = canonical_hash({"queue_hash": stored_q, "failures": failures})
    return record
