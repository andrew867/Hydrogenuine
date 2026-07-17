"""Waste elimination with receipts — no silent cleanup."""

from __future__ import annotations

import shutil
from pathlib import Path

from hg_runtime.wake_refresh.boot_hygiene import WORKSPACE, is_protected_path, normalize_rel
from hg_runtime.wake_refresh.receipts import new_waste_receipt
from hg_runtime.wake_refresh.schema import CleanupDecision, WasteClass, WasteEliminationReceipt, WakeHygieneState


def attempt_cleanup_path(path: Path, *, workspace: Path | None = None) -> tuple[bool, str]:
    ws = workspace or WORKSPACE
    rel = normalize_rel(path, ws)
    protected, reason = is_protected_path(rel)
    if protected:
        return False, reason
    if rel.startswith("docs/proofs"):
        return False, "RED_WAKE_REFRESH_DELETED_PROOF"
    try:
        if path.is_file():
            path.unlink()
            return True, "deleted_file"
        if path.is_dir():
            shutil.rmtree(path)
            return True, "deleted_dir"
    except OSError as exc:
        return False, str(exc)
    return False, "not_found"


def apply_cleanup(
    hygiene: WakeHygieneState,
    *,
    apply: bool,
    workspace: Path | None = None,
    epoch_id: str | None = None,
    max_items: int = 50,
) -> tuple[list[WasteEliminationReceipt], list[str], WakeHygieneState, bool]:
    ws = workspace or WORKSPACE
    receipts: list[WasteEliminationReceipt] = []
    failures: list[str] = []
    count = 0
    truncated = False

    for decision in hygiene.cleanup_decisions:
        if count >= max_items:
            truncated = True
            if not apply:
                failures.append("RED_WAKE_REFRESH_UNBOUNDED_CLEANUP")
            break
        if not decision.allowed:
            if "proof" in decision.reason.lower() or "protected" in decision.reason.lower():
                failures.append("RED_WAKE_REFRESH_DELETED_PROOF")
            continue
        path = ws / decision.path
        protected, reason = is_protected_path(decision.path)
        if protected:
            failures.append("RED_WAKE_REFRESH_DELETED_PROOF" if "proof" in reason else "RED_WAKE_REFRESH_AUTHORITY_CONVERSION")
            continue
        if apply:
            ok, method = attempt_cleanup_path(path, workspace=ws)
            if not ok:
                failures.append(method)
                continue
            decision.apply = True
            receipts.append(
                new_waste_receipt(
                    decision.path,
                    decision.waste_class,
                    decision.reason,
                    content_hash=None,
                    method=method,
                    epoch_id=epoch_id,
                )
            )
            count += 1
        else:
            receipts.append(
                new_waste_receipt(
                    decision.path,
                    decision.waste_class,
                    f"dry-run: {decision.reason}",
                    method="dry_run",
                    epoch_id=epoch_id,
                )
            )
            count += 1

    return receipts, failures, hygiene, truncated


__all__ = ["apply_cleanup", "attempt_cleanup_path"]
