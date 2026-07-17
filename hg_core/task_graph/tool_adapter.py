"""Native task tool adapter bridging DAG tool nodes to automation tasks."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from hg_core.job_registry import get_session_target
from hg_lib.config import get_workspace_root

from .tool_adapter_contract import ToolAdapter, ToolError, ToolResult
from .native_task_tools import run_task_tool

MAX_LEDGER_ENTRIES = 500


def _session_target_for_tool(tool_name: str) -> str:
    return get_session_target(tool_name) or f"automation-{tool_name}"


def _dedupe_path(tool_name: str) -> Optional[Path]:
    try:
        root = get_workspace_root()
    except Exception:
        return None
    return root / "memory" / "automation" / _session_target_for_tool(tool_name) / "post_dedupe.json"


def _load_ledger(path: Optional[Path]) -> Dict[str, Any]:
    if path is None or not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    return data if isinstance(data, dict) else {}


def _save_ledger(path: Optional[Path], data: Dict[str, Any]) -> None:
    if path is None:
        return
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except OSError:
        return


def _read_idempotency_hit(tool_name: str, idempotency_key: str) -> Optional[Dict[str, Any]]:
    path = _dedupe_path(tool_name)
    payload = _load_ledger(path)
    entries = payload.get("entries")
    if not isinstance(entries, dict):
        return None
    hit = entries.get(idempotency_key)
    if isinstance(hit, dict):
        return hit
    return None


def _record_idempotency_result(
    tool_name: str,
    idempotency_key: str,
    *,
    outputs: Dict[str, Any],
    usage: Optional[Dict[str, Any]],
    timeout_s: Optional[int],
) -> None:
    path = _dedupe_path(tool_name)
    payload = _load_ledger(path)
    entries = payload.get("entries")
    if not isinstance(entries, dict):
        entries = {}
    entries[idempotency_key] = {
        "at": datetime.now(timezone.utc).isoformat(),
        "tool_name": tool_name,
        "outputs": outputs,
        "usage": usage or {},
        "timeout_s": timeout_s,
    }
    if len(entries) > MAX_LEDGER_ENTRIES:
        ordered = sorted(
            entries.items(),
            key=lambda item: str((item[1] if isinstance(item[1], dict) else {}).get("at", "")),
        )
        entries = dict(ordered[-MAX_LEDGER_ENTRIES:])
    payload["entries"] = entries
    _save_ledger(path, payload)


class NativeTaskToolAdapter(ToolAdapter):
    """Invoke automation tasks via the existing native task tool helpers."""

    def invoke(
        self,
        tool_name: str,
        inputs: Dict[str, Any],
        *,
        idempotency_key: Optional[str] = None,
        timeout_s: Optional[int] = None,
    ) -> ToolResult:
        if idempotency_key:
            existing = _read_idempotency_hit(tool_name, idempotency_key)
            if existing is not None:
                existing_outputs = existing.get("outputs")
                existing_usage = existing.get("usage")
                metadata = {
                    "dedupe_hit": True,
                    "idempotency_key": idempotency_key,
                }
                return ToolResult(
                    ok=True,
                    outputs=existing_outputs if isinstance(existing_outputs, dict) else {},
                    usage=existing_usage if isinstance(existing_usage, dict) else None,
                    metadata=metadata,
                )

        tool_result = run_task_tool(tool_name, inputs, timeout_s=timeout_s or 300)
        if tool_result is None:
            return ToolResult(
                ok=False,
                outputs={},
                error=ToolError(
                    code="TOOL_NOT_AVAILABLE",
                    message="No execution path registered for this tool",
                ),
            )

        ok = bool(tool_result.get("ok"))
        outputs = tool_result.get("outputs") if isinstance(tool_result.get("outputs"), dict) else {}
        error_payload = tool_result.get("error")
        error_code = tool_result.get("error_code") or "TOOL_ERROR"
        if isinstance(error_payload, dict) and error_payload.get("code"):
            error_code = error_payload.get("code")
        if not ok and not error_payload:
            error_payload = tool_result.get("stderr") or tool_result.get("error")
        error = None
        if not ok:
            error = ToolError(code=str(error_code), message=str(error_payload or "tool invocation failed"))

        usage: Optional[Dict[str, Any]] = None
        if "external_calls" in tool_result or "tokens" in tool_result:
            usage = {}
            for key in ("external_calls", "tokens", "bytes_in", "bytes_out"):
                if key in tool_result:
                    usage[key] = tool_result[key]
            if not usage:
                usage = None

        metadata: Optional[Dict[str, Any]] = None
        if tool_result.get("returncode") is not None:
            metadata = {"returncode": tool_result.get("returncode")}

        if ok and idempotency_key:
            _record_idempotency_result(
                tool_name,
                idempotency_key,
                outputs=outputs or {},
                usage=usage,
                timeout_s=timeout_s,
            )

        return ToolResult(ok=ok, outputs=outputs or {}, error=error, usage=usage, metadata=metadata)


def _social_idempotency_key(tool_name: str, inputs: Dict[str, Any]) -> str:
    """Generate a stable idempotency key for L10 social tools when node does not provide one."""
    import hashlib
    import json
    payload = json.dumps(inputs, sort_keys=True, default=str)
    digest = hashlib.sha256(f"{tool_name}:{payload}".encode()).hexdigest()
    return f"dag-{digest[:24]}"


class CompositeToolAdapter(ToolAdapter):
    """
    Delegates to L10 social tool router for social.fourclaw.* / social.moltbook.*;
    otherwise uses NativeTaskToolAdapter for job-registry tasks.
    """

    def __init__(
        self,
        native: NativeTaskToolAdapter,
        social_tool_names: set[str],
        l10_idempotency_store: Any,
    ) -> None:
        self._native = native
        self._social_names = social_tool_names
        self._l10_store = l10_idempotency_store

    def invoke(
        self,
        tool_name: str,
        inputs: Dict[str, Any],
        *,
        idempotency_key: Optional[str] = None,
        timeout_s: Optional[int] = None,
    ) -> ToolResult:
        if tool_name not in self._social_names:
            return self._native.invoke(
                tool_name, inputs, idempotency_key=idempotency_key, timeout_s=timeout_s
            )
        # L10 social path: ToolCall -> execute -> map result to ToolResult
        try:
            from hg_realtime.integrations.tool_registry import build_default_registry
            from hg_realtime.integrations.tool_router import ToolCall, execute
        except ImportError as e:
            return ToolResult(
                ok=False,
                outputs={},
                error=ToolError(code="L10_UNAVAILABLE", message=str(e)),
            )
        key = idempotency_key or _social_idempotency_key(tool_name, inputs)
        if len(key) < 8:
            key = _social_idempotency_key(tool_name, inputs)
        call = ToolCall(
            tool_name=tool_name,
            args=dict(inputs),
            idempotency_key=key,
            correlation_id="dag",
            run_id="dag",
        )
        try:
            reg = build_default_registry()
            raw = execute(call, reg, self._l10_store)
        except Exception as e:
            return ToolResult(
                ok=False,
                outputs={},
                error=ToolError(code="L10_ERROR", message=str(e)),
            )
        ok = bool(raw.get("ok"))
        data = raw.get("data")
        outputs = data if isinstance(data, dict) else (raw if isinstance(raw, dict) else {})
        if not isinstance(outputs, dict):
            outputs = {}
        err = raw.get("error")
        error = None
        if not ok and err is not None:
            error = ToolError(
                code=getattr(err, "code", "TOOL_ERROR") if hasattr(err, "code") else "TOOL_ERROR",
                message=str(err),
            )
        return ToolResult(ok=ok, outputs=outputs, error=error)
