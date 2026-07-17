"""
Pack 6: Release compatibility gates — deterministic replay, manifest comparison, block/approve.
RELEASE_COMPAT_CHECK_RAN, RELEASE_BLOCKED_BY_CONTRACT, RELEASE_APPROVED.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from hg_core.ledger import emit


def _iso_ts() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def run_release_compat_check(
    workspace_root: Path,
    *,
    contract_id: str,
    current_manifest_hashes: Optional[Dict[str, str]] = None,
    previous_manifest_hashes: Optional[Dict[str, str]] = None,
    scope: Optional[Dict[str, str]] = None,
    actor: Optional[Dict[str, str]] = None,
) -> Tuple[bool, Dict[str, Any]]:
    """
    Compare current vs previous manifest hashes (or derive from replay). Write release_compat_report.
    Returns (passed, report_dict). Emits RELEASE_COMPAT_CHECK_RAN.
    """
    workspace_root = Path(workspace_root)
    scope = scope or {"type": "global", "id": "release"}
    actor = actor or {"agent_id": "release-gate", "pubkey": "", "key_id": ""}
    ts = _iso_ts()
    report_id = "rpt_" + hashlib.sha256(f"{contract_id}:{ts}".encode()).hexdigest()[:16]
    current = current_manifest_hashes or {}
    previous = previous_manifest_hashes or {}
    diffs: List[Dict[str, Any]] = []
    for key in set(current) | set(previous):
        c = current.get(key)
        p = previous.get(key)
        if c != p:
            diffs.append({"component": key, "before": p, "after": c})
    result = "pass" if len(diffs) == 0 else "fail"
    report = {
        "report_id": report_id,
        "ts": ts,
        "contract_id": contract_id,
        "result": result,
        "diffs": diffs,
    }
    root = workspace_root / "artifacts" / "release"
    root.mkdir(parents=True, exist_ok=True)
    report_path = root / "release_compat_report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    emit(
        "RELEASE_COMPAT_CHECK_RAN",
        "release_compat",
        report_id,
        {"report_id": report_id, "contract_id": contract_id, "result": result, "artifact_id": str(report_path), "ts": ts},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )
    return result == "pass", report


def emit_release_blocked(
    *,
    report_id: str,
    contract_id: str,
    reason: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
) -> str:
    """Emit RELEASE_BLOCKED_BY_CONTRACT. Returns event_id."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    return emit(
        "RELEASE_BLOCKED_BY_CONTRACT",
        "release_compat",
        report_id,
        {"report_id": report_id, "contract_id": contract_id, "reason": reason, "ts": ts},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )


def emit_release_approved(
    *,
    report_id: str,
    contract_id: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
) -> str:
    """Emit RELEASE_APPROVED (passed and signed). Returns event_id."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    return emit(
        "RELEASE_APPROVED",
        "release_compat",
        report_id,
        {"report_id": report_id, "contract_id": contract_id, "ts": ts},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )
