"""
OS Phase 1: Executable policy engine. Evaluates context -> allow/deny/require_approval/cost_multiplier/tool_allowlist.
Simulation runs scenarios before publish.
"""

from pathlib import Path
from typing import Any, Dict

from .engine import PolicyEngine

__all__ = ["PolicyEngine"]


def load_engine(path: Path) -> PolicyEngine:
    return PolicyEngine.load(str(path))
