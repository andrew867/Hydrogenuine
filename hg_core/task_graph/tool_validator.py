"""Tool contract validation: validate_tool_call (before invoke) and validate_tool_result (after)."""

from __future__ import annotations

from typing import Any, Dict, Optional

from .tool_registry import ToolDescriptor, ToolRegistry
from .tool_adapter_contract import ToolResult


class ToolContractError(Exception):
    """Raised when tool call or result violates the contract."""

    pass


def validate_tool_call(
    registry: ToolRegistry,
    tool_name: str,
    inputs: Dict[str, Any],
    *,
    idempotency_key: Optional[str],
    retries: int,
    in_loop_body: bool,
) -> Dict[str, Any]:
    """
    Validate a tool call before invoke. Raises ToolContractError on violation.
    Returns dict with timeout_s from descriptor for caller to pass to invoke.
    """
    desc = registry.get(tool_name)

    if not isinstance(inputs, dict):
        raise ToolContractError("inputs must be dict")

    if desc.effect_class == "write" and (retries > 0 or in_loop_body):
        if not idempotency_key:
            raise ToolContractError(
                "write tool with retries or loop requires idempotency_key"
            )
        if not desc.supports_idempotency_key:
            raise ToolContractError("tool does not support idempotency_key")

    return {"timeout_s": desc.default_timeout_s}


def validate_tool_result(
    desc: ToolDescriptor,
    result: ToolResult,
    strict: bool = False,
) -> None:
    """
    Validate a tool result after invoke. Raises ToolContractError if result is invalid.
    In strict mode, outputs can be validated against output_schema (MVP: only ok/error check).
    """
    if not result.ok and result.error is None:
        raise ToolContractError("tool result not ok but no error provided")
