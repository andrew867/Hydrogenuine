"""Disposable sandbox patch dry-run mechanics."""

from __future__ import annotations

import shutil
from pathlib import Path

from hg_runtime.memory_ledger.hash_chain import canonical_hash
from hg_runtime.operator_review_queue.permit import validate_permit
from hg_runtime.operator_review_queue.schemas import (
    DRY_RUN_APPLY_COMPLETED,
    DRY_RUN_REQUEST_SCHEMA,
    DRY_RUN_RESULT_SCHEMA,
    QUEUED_FOR_OPERATOR_REVIEW,
    REJECTED_LIVE_REPO_MUTATION,
    REJECTED_NO_OPERATOR_PERMIT,
    SANDBOX_RECORD_SCHEMA,
    neutral_flags,
)


def dry_run_request(queue_item: dict, permit: dict | None, sandbox_path: Path, *, live_repo_target: bool = False) -> dict:
    req = {
        "schema": DRY_RUN_REQUEST_SCHEMA,
        "dry_run_request_id": "dryrun-request-" + queue_item["source_patch_candidate_id"].lower(),
        "queue_item_id": queue_item["queue_item_id"],
        "permit_id": permit.get("permit_id") if permit else None,
        "sandbox_path": str(sandbox_path),
        "sandbox_only": not live_repo_target,
        "live_repo_target": live_repo_target,
        **neutral_flags(),
    }
    req["dry_run_request_hash"] = canonical_hash(req)
    return req


def _target_from_patch(patch_text: str) -> str:
    for line in patch_text.splitlines():
        if line.startswith("+++ b/"):
            return line[6:].strip()
    return "UNKNOWN"


def apply_dry_run(queue_item: dict, permit: dict | None, sandbox_path: Path, *, live_repo_target: bool = False) -> tuple[dict, dict]:
    validation = validate_permit(queue_item, permit)
    if live_repo_target:
        result = REJECTED_LIVE_REPO_MUTATION
        changed: list[str] = []
    elif queue_item["queued_status"] != QUEUED_FOR_OPERATOR_REVIEW:
        result = queue_item["queued_status"]
        changed = []
    elif not validation["valid"]:
        result = validation["decision"] if validation["decision"] != "VALID_OPERATOR_PERMIT_FIXTURE" else REJECTED_NO_OPERATOR_PERMIT
        changed = []
    else:
        target = _target_from_patch(queue_item["patch_text"])
        out = sandbox_path / target
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text("PHASE41_SANDBOX_DRY_RUN_ONLY\n" + queue_item["patch_text"], encoding="utf-8")
        result = DRY_RUN_APPLY_COMPLETED
        changed = [target]
    sandbox = {
        "schema": SANDBOX_RECORD_SCHEMA,
        "sandbox_id": "sandbox-" + queue_item["source_patch_candidate_id"].lower(),
        "sandbox_path": str(sandbox_path),
        "sandbox_only": not live_repo_target,
        "live_repo_mutated": False,
        "files_changed_in_sandbox": changed,
        **neutral_flags(),
    }
    sandbox["sandbox_hash"] = canonical_hash(sandbox)
    row = {
        "schema": DRY_RUN_RESULT_SCHEMA,
        "dry_run_id": "dryrun-" + queue_item["source_patch_candidate_id"].lower(),
        "queue_item_id": queue_item["queue_item_id"],
        "permit_id": permit.get("permit_id") if permit else None,
        "sandbox_path": str(sandbox_path),
        "sandbox_only": not live_repo_target,
        "live_repo_mutated": False,
        "files_changed_in_sandbox": changed,
        "rollback_available": bool(changed),
        "rollback_performed": False,
        "result": result,
        **neutral_flags(),
    }
    row["dry_run_result_hash"] = canonical_hash(row)
    return row, sandbox


def remove_sandbox(path: Path) -> bool:
    if path.exists():
        shutil.rmtree(path)
    return not path.exists()
