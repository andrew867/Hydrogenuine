"""Tool router: validate ToolCall (idempotency_key required), execute via registry with idempotency store."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from .idempotency_store import IdempotencyStore


@dataclass(frozen=True)
class ToolCall:
    tool_name: str
    args: Dict[str, Any]
    idempotency_key: str
    correlation_id: str
    run_id: str
    node_id: Optional[str] = None


class ToolRouterEnforcer:
    """Validates tool calls (idempotency_key required)."""

    def validate(self, call: ToolCall) -> None:
        if not call.idempotency_key or len(call.idempotency_key) < 8:
            raise ValueError("idempotency_key is required for all tool calls (min 8 chars)")


def execute(
    call: ToolCall,
    registry: Any,
    idempotency_store: IdempotencyStore,
    enforcer: Optional[ToolRouterEnforcer] = None,
    ttl_seconds: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Resolve handler from registry, validate (idempotency_key required), check store;
    if hit return cached result; else run handler, write store, return result.
    """
    enforcer = enforcer or ToolRouterEnforcer()
    enforcer.validate(call)
    cached = idempotency_store.get(call.idempotency_key)
    if cached is not None:
        return cached
    entry = registry.get(call.tool_name)
    result = entry.handler(call)
    idempotency_store.set(call.idempotency_key, result, ttl_seconds=ttl_seconds)
    return result
