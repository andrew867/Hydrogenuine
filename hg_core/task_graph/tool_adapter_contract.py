"""Tool adapter contract: ToolResult, ToolError, ToolAdapter.invoke."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class ToolError:
    code: str
    message: str


@dataclass
class ToolResult:
    ok: bool
    outputs: Dict[str, Any]
    error: Optional[ToolError] = None
    usage: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


class ToolAdapter(ABC):
    """
    Adapter contract for tool execution.

    Implementations are expected to:
    - accept canonical tool_name + dict inputs
    - honor idempotency_key for write-like retries when supported
    - honor timeout_s when provided by validator/descriptor defaults
    - always return ToolResult with outputs as a dict
    - return ToolResult(ok=False, error=ToolError(...)) on failure
    """

    @abstractmethod
    def invoke(
        self,
        tool_name: str,
        inputs: Dict[str, Any],
        *,
        idempotency_key: Optional[str] = None,
        timeout_s: Optional[int] = None,
    ) -> ToolResult:
        ...


class StubToolAdapter(ToolAdapter):
    """Default adapter that returns success with empty outputs (for tests or when no real tools)."""

    def invoke(
        self,
        tool_name: str,
        inputs: Dict[str, Any],
        *,
        idempotency_key: Optional[str] = None,
        timeout_s: Optional[int] = None,
    ) -> ToolResult:
        return ToolResult(ok=True, outputs={})
