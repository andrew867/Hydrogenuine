"""Rollback records for sandbox dry-run applies."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.memory_ledger.hash_chain import canonical_hash
from hg_runtime.operator_review_queue.sandbox_apply import remove_sandbox
from hg_runtime.operator_review_queue.schemas import DRY_RUN_APPLY_ROLLED_BACK, ROLLBACK_RECORD_SCHEMA, neutral_flags


def rollback_record(dry_run_result: dict, sandbox_path: Path) -> dict:
    restored = remove_sandbox(sandbox_path)
    row = {
        "schema": ROLLBACK_RECORD_SCHEMA,
        "rollback_id": "rollback-" + dry_run_result["queue_item_id"],
        "dry_run_id": dry_run_result["dry_run_id"],
        "sandbox_path": str(sandbox_path),
        "rollback_performed": True,
        "sandbox_clean": restored,
        "result": DRY_RUN_APPLY_ROLLED_BACK,
        **neutral_flags(),
    }
    row["rollback_hash"] = canonical_hash(row)
    return row
