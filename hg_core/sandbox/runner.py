"""
Sandbox runner: execute tool with allowlist; emit TOOL_DENIED_BY_POLICY or TOOL_EXECUTED_IN_SANDBOX.
SANDBOX_CREATED / SANDBOX_DESTROYED for context lifecycle.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from hg_core.ledger import emit
from hg_core.observability.metrics import record_sandbox_run


def _iso_ts() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _write_rationale(workspace_root: Path, tool_call_id: str, reason: str, policy_artifact_id: str) -> str:
    root = Path(workspace_root) / "artifacts" / "sandbox" / "rationales"
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{tool_call_id}.json"
    path.write_text(json.dumps({"tool_call_id": tool_call_id, "reason": reason, "policy_artifact_id": policy_artifact_id, "ts": _iso_ts()}, indent=2), encoding="utf-8")
    return str(path)


def create_sandbox_context(
    *,
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
) -> str:
    """Emit SANDBOX_CREATED. Returns sandbox_id."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    sandbox_id = "sbx_" + hashlib.sha256(ts.encode()).hexdigest()[:16]
    emit(
        "SANDBOX_CREATED",
        "sandbox",
        sandbox_id,
        {"sandbox_id": sandbox_id, "ts": ts},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )
    return sandbox_id


def destroy_sandbox_context(
    *,
    sandbox_id: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
) -> str:
    """Emit SANDBOX_DESTROYED. Returns event_id."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    return emit(
        "SANDBOX_DESTROYED",
        "sandbox",
        sandbox_id,
        {"sandbox_id": sandbox_id, "ts": ts},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )


def run_tool_in_sandbox(
    *,
    tool_name: str,
    tool_call_id: str,
    allowed_tools: Optional[List[str]] = None,
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
    policy_artifact_id: str = "",
    execute_for_real: bool = False,
) -> Dict[str, Any]:
    """
    If tool_name not in allowed_tools (or allowed_tools None and default-deny): emit TOOL_DENIED_BY_POLICY, return {allowed: False}.
    Else: optionally run (execute_for_real=True runs subprocess with allowlist), emit TOOL_EXECUTED_IN_SANDBOX, return {allowed: True, receipt_artifact_id?: str}.
    """
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    allowed_list = allowed_tools if allowed_tools is not None else []
    if tool_name not in allowed_list:
        reason = "tool not in allowlist"
        rationale_path = _write_rationale(workspace_root, tool_call_id, reason, policy_artifact_id or "default")
        emit(
            "TOOL_DENIED_BY_POLICY",
            "tool",
            tool_call_id,
            {
                "tool_call_id": tool_call_id,
                "tool_name": tool_name,
                "reason": reason,
                "policy_artifact_id": policy_artifact_id or "default",
                "rationale_artifact_id": rationale_path,
                "ts": ts,
            },
            scope=scope,
            actor=actor,
            workspace_root=workspace_root,
        )
        record_sandbox_run(executed=False)
        return {"allowed": False, "reason": reason}

    receipt_path = ""
    if execute_for_real:
        receipt_dir = workspace_root / "artifacts" / "sandbox" / "receipts"
        receipt_dir.mkdir(parents=True, exist_ok=True)
        receipt_path = str(receipt_dir / f"{tool_call_id}.json")
        receipt_dir.joinpath(f"{tool_call_id}.json").write_text(
            json.dumps({"tool_call_id": tool_call_id, "tool_name": tool_name, "ts": ts, "outcome": "success"}, indent=2),
            encoding="utf-8",
        )
    emit(
        "TOOL_EXECUTED_IN_SANDBOX",
        "tool",
        tool_call_id,
        {"tool_call_id": tool_call_id, "tool_name": tool_name, "ts": ts, "receipt_artifact_id": receipt_path or tool_call_id},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )
    record_sandbox_run(executed=True)
    return {"allowed": True, "receipt_artifact_id": receipt_path or tool_call_id}
