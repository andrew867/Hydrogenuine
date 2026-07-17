"""DURABLE_LOCAL_FILE_SINK — sandbox-scoped file writes with receipt."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from hg_core.dse.config import dse_file_sink_root, ensure_sandbox_dirs
from hg_core.dse.errors import DSE_ROLLBACK_RECORDED, DSE_SINK_COMMITTED, REFUSED_UNAUTHORIZED_PATH
from hg_core.dse.no_authority import advisory_only_marker
from hg_core.dse.policy import SinkClass
from hg_core.dse.sandbox import deterministic_filename, validate_path_in_sandbox
from hg_core.dse.types import DurableSinkReceipt, SinkRollbackRecord
from hg_core.governance.canonical_hash import canonical_hash
from hg_core.policy_safety.hashing import compute_record_hash


def write_durable_file(
    *,
    request_id: str,
    tranche_id: str,
    relative_name: str,
    content: dict[str, Any],
    observed_at: str,
    allowed_root: Path | None = None,
) -> dict[str, Any]:
    """Write JSON content to sandbox file sink; emit receipt and rollback marker."""
    ensure_sandbox_dirs()
    root = allowed_root or dse_file_sink_root()
    ok, reason, target = validate_path_in_sandbox(relative_name, allowed_root=root)
    if not ok or target is None:
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": reason or REFUSED_UNAUTHORIZED_PATH,
            "durable_write_performed": False,
        }

    backup_path = target.with_suffix(target.suffix + ".rollback")
    if target.exists():
        backup_path.write_bytes(target.read_bytes())

    body = json.dumps(content, indent=2, sort_keys=True) + "\n"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(body, encoding="utf-8")
    content_digest = canonical_hash({"content": content})

    receipt_id = f"dse-file-{compute_record_hash({'request_id': request_id, 'target': str(target)})[-12:]}"
    rollback_id = f"dse-rbk-{receipt_id[-12:]}"
    rollback_marker = root / deterministic_filename("rollback", request_id)
    rollback_marker.write_text(
        json.dumps({"receipt_id": receipt_id, "backup": str(backup_path), "target": str(target)}, indent=2) + "\n",
        encoding="utf-8",
    )

    receipt = DurableSinkReceipt(
        receipt_id=receipt_id,
        sink_class=SinkClass.DURABLE_LOCAL_FILE_SINK.value,
        tranche_id=tranche_id,
        request_id=request_id,
        target_ref=str(target.relative_to(root)),
        content_digest=content_digest,
        rollback_marker_ref=str(rollback_marker.relative_to(root)),
        observed_at=observed_at,
    )
    rollback = SinkRollbackRecord(
        rollback_id=rollback_id,
        receipt_id=receipt_id,
        tranche_id=tranche_id,
        target_ref=str(target.relative_to(root)),
        rollback_digest=canonical_hash({"backup": str(backup_path)}),
        observed_at=observed_at,
    )

    return {
        **advisory_only_marker(),
        "status": "committed",
        "reason_code": DSE_SINK_COMMITTED,
        "sink_class": SinkClass.DURABLE_LOCAL_FILE_SINK.value,
        "durable_write_performed": True,
        "receipt": receipt.to_payload(),
        "rollback": rollback.to_payload(),
        "rollback_reason_code": DSE_ROLLBACK_RECORDED,
        "observed_at": observed_at,
    }


__all__ = ["write_durable_file"]
