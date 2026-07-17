"""
Signal registry: load and resolve signal definitions for the observation pipeline.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import yaml
except ImportError:
    yaml = None


@dataclass(frozen=True)
class SignalDefinition:
    signal_id: str
    name: str
    type: str
    schema: Dict[str, Any]
    reliability: float
    pii_class: str
    retention_policy_id: str
    description: str = ""
    units: Optional[str] = None
    expected_range: Optional[Dict[str, Any]] = None
    sampling: Optional[Dict[str, Any]] = None

    def __post_init__(self) -> None:
        if self.type not in ("text", "log", "metric", "http", "file", "event"):
            raise ValueError(f"Invalid signal type: {self.type}")
        if self.pii_class not in ("none", "low", "medium", "high"):
            raise ValueError(f"Invalid pii_class: {self.pii_class}")
        if not 0 <= self.reliability <= 1:
            raise ValueError("reliability must be 0..1")


class SignalRegistry:
    def __init__(self, defs: Dict[str, SignalDefinition]) -> None:
        self._defs = dict(defs)

    def get(self, signal_id: str) -> SignalDefinition:
        if signal_id not in self._defs:
            raise KeyError(f"Unknown signal_id: {signal_id}")
        return self._defs[signal_id]

    def list_ids(self) -> List[str]:
        return list(self._defs.keys())

    def __contains__(self, signal_id: str) -> bool:
        return signal_id in self._defs


def load_registry(path: Path) -> SignalRegistry:
    """Load signal registry from YAML file. Path can be str or Path."""
    path = Path(path)
    if not path.exists():
        return SignalRegistry({})
    if yaml is None:
        return SignalRegistry({})
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    defs: Dict[str, SignalDefinition] = {}
    for item in data.get("signals", []):
        sd = SignalDefinition(
            signal_id=item["signal_id"],
            name=item["name"],
            type=item["type"],
            schema=item.get("schema", {}),
            reliability=float(item.get("reliability", 0.5)),
            pii_class=item.get("pii_class", "none"),
            retention_policy_id=item.get("retention_policy_id", "default"),
            description=item.get("description", ""),
            units=item.get("units"),
            expected_range=item.get("expected_range"),
            sampling=item.get("sampling"),
        )
        defs[sd.signal_id] = sd
    return SignalRegistry(defs)
