"""Phase 38 work-package loader.

Loads a Phase 37 generated work package (from disk or as an inline dict) and
decides whether it is eligible to produce a patch candidate. Only a READY
package is eligible; NOT_READY / LIVE_SELF_BLOCKED / RED_REFUSED packages are
refused for patch generation with the mapped decision.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from hg_runtime.patch_candidate_sandbox.schemas import (
    NOT_READY_DECISION_BY_SOURCE_STATUS,
    UNKNOWN,
)

STATUS_READY = "READY"


def load_work_package(source: Any) -> dict[str, Any]:
    """Normalize a work-package source into a Phase 38 source descriptor."""
    if isinstance(source, Mapping):
        record = dict(source)
    else:
        record = _load_from_dir(Path(source))

    status = str(record.get("status") or record.get("candidate_status") or UNKNOWN)
    source_id = str(record.get("proposal_id") or record.get("source_work_package_id") or UNKNOWN)
    source_hash = str(record.get("package_hash") or record.get("source_work_package_hash") or UNKNOWN)
    is_ready = status == STATUS_READY
    refusal_decision = None if is_ready else NOT_READY_DECISION_BY_SOURCE_STATUS.get(status)
    return {
        "source_work_package_id": source_id,
        "source_work_package_hash": source_hash,
        "source_status": status,
        "is_ready": is_ready,
        "refusal_decision": refusal_decision,
        "eligible_for_patch_candidate": is_ready,
    }


def _load_from_dir(path: Path) -> dict[str, Any]:
    receipt_path = path / "compiler_receipt.json"
    if not receipt_path.is_file():
        return {"proposal_id": path.name, "status": UNKNOWN, "package_hash": UNKNOWN}
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    return {
        "proposal_id": receipt.get("proposal_id", path.name),
        "status": receipt.get("status", UNKNOWN),
        "package_hash": receipt.get("package_hash", UNKNOWN),
    }


__all__ = ["load_work_package"]
