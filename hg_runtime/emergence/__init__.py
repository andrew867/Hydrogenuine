"""Emergence Lifecycle Sequence — formal wake/bootstrap protocol."""

from hg_runtime.emergence.config import ELSConfig, els_enabled
from hg_runtime.emergence.handler import Phase1ELSHandler, StubELSHandler
from hg_runtime.emergence.lifecycle import can_transition, run_wake_cycle
from hg_runtime.emergence.report import build_wake_report
from hg_runtime.emergence.subagents import run_subagent_wake
from hg_runtime.emergence.types import WakeRequest, WakeResult

__all__ = [
    "ELSConfig",
    "Phase1ELSHandler",
    "StubELSHandler",
    "WakeRequest",
    "WakeResult",
    "build_wake_report",
    "can_transition",
    "els_enabled",
    "run_subagent_wake",
    "run_wake_cycle",
]
