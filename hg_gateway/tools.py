"""
Gateway tool registry and execution: share hg_core tool contract when available.
Exposes tool list with schemas and invokes tools via the same adapter used by DAG runtime.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict, List, Optional, Tuple

_registry: Any = None
_adapter: Any = None
_build_mode: str = "uninitialized"
_build_error: Optional[str] = None


def _strict_runtime_required() -> bool:
    """Match hg_gateway.auth strict production-like environments."""
    import os

    env = (os.environ.get("HG_ENV", "Demo") or "Demo").strip().lower()
    dev = os.environ.get("HG_GATEWAY_DEV", "").strip().lower() in ("1", "true", "yes")
    return env not in {"demo", "dev", "development", "test", "testing"} and not dev


def _build() -> Tuple[Any, Any]:
    """Build registry and adapter from hg_core or fallback to stub."""
    global _build_mode, _build_error
    from hg_core.task_graph.tool_registry import ToolRegistry, ToolDescriptor
    from hg_core.task_graph.tool_adapter_contract import StubToolAdapter, ToolAdapter, ToolResult
    gateway_echo = ToolDescriptor(
        name="gateway.echo",
        description="Echo inputs (gateway stub for tests and demos)",
        input_schema={"type": "object", "properties": {"message": {"type": "string"}}},
        output_schema={"type": "object"},
        effect_class="none",
        supports_idempotency_key=False,
        default_timeout_s=10,
        rate_limit=None,
    )
    stub = StubToolAdapter()
    class GatewayEchoAdapter(ToolAdapter):
        """Wraps delegate; handles gateway.echo with stub so it always works."""
        def __init__(self, delegate: ToolAdapter) -> None:
            self._delegate = delegate
        def invoke(self, tool_name: str, inputs: Dict[str, Any], *, idempotency_key: Optional[str] = None, timeout_s: Optional[int] = None) -> ToolResult:
            if tool_name == "gateway.echo":
                return stub.invoke(tool_name, inputs, idempotency_key=idempotency_key, timeout_s=timeout_s)
            return self._delegate.invoke(tool_name, inputs, idempotency_key=idempotency_key, timeout_s=timeout_s)
    try:
        from hg_core.task_graph.tool_contract_setup import build_default_tool_contract
        registry, adapter = build_default_tool_contract()
        try:
            registry.register(gateway_echo)
        except ValueError:
            pass
        _build_mode = "default_contract"
        _build_error = None
        return registry, GatewayEchoAdapter(adapter)
    except Exception as exc:
        _build_mode = "stub_fallback"
        _build_error = str(exc)
        if _strict_runtime_required():
            raise RuntimeError(
                "Gateway refuses stub tool adapter fallback in non-demo mode. "
                f"build_default_tool_contract failed: {exc}"
            ) from exc
    from hg_core.task_graph.tool_registry import ToolRegistry
    from hg_core.task_graph.tool_adapter_contract import StubToolAdapter

    registry = ToolRegistry()
    registry.register(gateway_echo)
    adapter = StubToolAdapter()
    print(f"[gateway.tools] WARNING using stub fallback adapter (demo/test only): {_build_error or 'unknown error'}")
    return registry, adapter


def get_registry_and_adapter() -> Tuple[Any, Any]:
    global _registry, _adapter
    if _registry is None or _adapter is None:
        _registry, _adapter = _build()
    return _registry, _adapter


def get_runtime_diagnostics() -> Dict[str, Any]:
    registry, adapter = get_registry_and_adapter()
    try:
        registry_size = len(registry.describe_all())
    except Exception:
        registry_size = None
    adapter_name = adapter.__class__.__name__ if adapter is not None else None
    return {
        "build_mode": _build_mode,
        "build_error": _build_error,
        "adapter_class": adapter_name,
        "registry_size": registry_size,
        "stub_fallback_active": bool(_build_mode == "stub_fallback" or adapter_name == "StubToolAdapter"),
    }


def list_tools() -> List[Dict[str, Any]]:
    """Return tool descriptors with schemas for API."""
    registry, _ = get_registry_and_adapter()
    try:
        return registry.describe_all()
    except Exception:
        return []


def get_tool_descriptor(tool_name: str) -> Optional[Dict[str, Any]]:
    """Return descriptor for tool_name or None."""
    registry, _ = get_registry_and_adapter()
    try:
        desc = registry.get(tool_name)
        if hasattr(desc, "__dataclass_fields__"):
            return asdict(desc)
        return {
            "name": getattr(desc, "name", tool_name),
            "description": getattr(desc, "description", ""),
            "input_schema": getattr(desc, "input_schema", {}),
            "output_schema": getattr(desc, "output_schema", {}),
            "effect_class": getattr(desc, "effect_class", "read"),
        }
    except (KeyError, Exception):
        return None


def invoke_tool(
    tool_name: str,
    inputs: Dict[str, Any],
    *,
    idempotency_key: Optional[str] = None,
    timeout_s: Optional[int] = None,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """
    Invoke a tool via the shared adapter. Returns dict with ok, outputs, error (if any).
    When dry_run=True, returns preview without executing (for approvals preview/testing).
    """
    if dry_run:
        desc = get_tool_descriptor(tool_name)
        return {
            "ok": True,
            "dry_run": True,
            "tool_name": tool_name,
            "inputs": inputs or {},
            "effect_class": (desc or {}).get("effect_class", "write"),
            "outputs": {},
        }
    diag = get_runtime_diagnostics()
    if diag.get("stub_fallback_active") and tool_name != "gateway.echo":
        return {
            "ok": False,
            "outputs": {},
            "error": {
                "code": "tool_runtime_unavailable",
                "message": (
                    "Tool execution blocked: gateway is running with stub fallback adapter. "
                    f"build_error={diag.get('build_error') or 'unknown'}. "
                    "Fix tool contract setup or run in demo mode."
                ),
            },
        }
    _, adapter = get_registry_and_adapter()
    result = adapter.invoke(
        tool_name,
        inputs or {},
        idempotency_key=idempotency_key,
        timeout_s=timeout_s,
    )
    out: Dict[str, Any] = {"ok": result.ok, "outputs": result.outputs or {}}
    if result.error:
        out["error"] = {"code": result.error.code, "message": result.error.message}
    if result.usage:
        out["usage"] = result.usage
    return out


def effect_class_for_tool(tool_name: str) -> str:
    """Return effect_class (none|read|write) for policy gating."""
    desc = get_tool_descriptor(tool_name)
    if not desc:
        return "write"
    return desc.get("effect_class", "write")
