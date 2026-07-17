"""Tool registry and descriptors for the tool contract layer."""

from __future__ import annotations

from dataclasses import asdict
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

VALID_EFFECT_CLASSES = {"none", "read", "write"}


@dataclass
class ToolDescriptor:
    name: str
    description: str
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    effect_class: str  # none|read|write
    supports_idempotency_key: bool = False
    default_timeout_s: int = 30
    rate_limit: Optional[Dict[str, Any]] = None


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: Dict[str, ToolDescriptor] = {}

    def register(self, desc: ToolDescriptor) -> None:
        if not isinstance(desc, ToolDescriptor):
            raise TypeError("ToolRegistry.register expects ToolDescriptor")
        if not isinstance(desc.name, str) or not desc.name.strip():
            raise ValueError("ToolDescriptor.name must be a non-empty string")
        if desc.name in self._tools:
            raise ValueError(f"Duplicate tool registration: {desc.name}")
        if desc.effect_class not in VALID_EFFECT_CLASSES:
            raise ValueError(
                f"Invalid effect_class '{desc.effect_class}' for tool {desc.name}; "
                f"expected one of {sorted(VALID_EFFECT_CLASSES)}"
            )
        if not isinstance(desc.default_timeout_s, int) or desc.default_timeout_s <= 0:
            raise ValueError(f"ToolDescriptor.default_timeout_s must be > 0 for tool {desc.name}")
        if not isinstance(desc.input_schema, dict) or not isinstance(desc.output_schema, dict):
            raise ValueError(f"ToolDescriptor schemas must be dict for tool {desc.name}")
        if not isinstance(desc.supports_idempotency_key, bool):
            raise ValueError(
                f"ToolDescriptor.supports_idempotency_key must be bool for tool {desc.name}"
            )
        if desc.rate_limit is not None:
            if not isinstance(desc.rate_limit, dict):
                raise ValueError(f"ToolDescriptor.rate_limit must be dict for tool {desc.name}")
            rpm = desc.rate_limit.get("requests_per_minute")
            burst = desc.rate_limit.get("burst")
            if rpm is not None and (not isinstance(rpm, int) or rpm <= 0):
                raise ValueError(
                    f"ToolDescriptor.rate_limit.requests_per_minute must be > 0 for tool {desc.name}"
                )
            if burst is not None and (not isinstance(burst, int) or burst <= 0):
                raise ValueError(f"ToolDescriptor.rate_limit.burst must be > 0 for tool {desc.name}")
        self._tools[desc.name] = desc

    def get(self, name: str) -> ToolDescriptor:
        if name not in self._tools:
            raise KeyError(f"Unknown tool: {name}")
        return self._tools[name]

    def list(self) -> List[ToolDescriptor]:
        return [self._tools[name] for name in sorted(self._tools.keys())]

    def describe_all(self) -> List[Dict[str, Any]]:
        """Return deterministic descriptor metadata for audits and UI summaries."""
        return [asdict(tool) for tool in self.list()]
