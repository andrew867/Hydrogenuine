"""LEB-5 evidence review queue replay.

Recomputes review task hashes and confirms the manifest task-hash list is
preserved. Asserts no forbidden boundary flag flipped true.
"""

from __future__ import annotations

from hg_runtime.local_evidence_bridge.schemas import (
    EvidenceBridgeError,
    assert_neutral,
    neutral_flags,
    record_hash,
)


def replay_review_queue(tasks: list[dict], manifest: dict) -> dict:
    failures: list[str] = []
    if [t["record_hash"] for t in tasks] != manifest.get("task_hashes", []):
        failures.append("task_hash_list_mismatch")
    for task in tasks:
        expected = record_hash({k: v for k, v in task.items() if k != "record_hash"})
        if task["record_hash"] != expected:
            failures.append(f"task_hash_mismatch:{task.get('review_task_id')}")
    try:
        for task in tasks:
            assert_neutral(task)
        assert_neutral(manifest)
    except EvidenceBridgeError as exc:
        failures.append(f"boundary_violation:{exc}")
    return {
        "schema_version": "1",
        "record_type": "evidence_review_replay_v1",
        "replay_id": "leb5-evidence-review-replay",
        "replay_preserves_review_hashes": not failures,
        "failures": failures,
        **neutral_flags(),
    }
