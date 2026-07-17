"""P26 recall replay helpers."""

from __future__ import annotations

from hg_runtime.experience_ledger.hashing import stable_hash
from hg_runtime.experience_ledger.recall_surface import build_recall_surface_run


def replay_recall(queries: list[dict], recall_index: dict, expected_root: str | None = None) -> dict:
    run = build_recall_surface_run(queries, recall_index)
    root = stable_hash({"query_hashes": [q["recall_hash"] for q in queries], "result_hashes": [r["recall_hash"] for r in run["results"]]})
    return {
        "record_type": "recall_replay_result_v1",
        "schema_version": "1",
        "replay_preserves_recall_hashes": expected_root is None or root == expected_root,
        "recall_replay_root": root,
        "read_only": True,
        "recall_treated_as_authority": False,
        "memory_treated_as_truth": False,
    }

