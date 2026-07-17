"""Bounded soak supervisor for Agent Zero governed sessions."""

from hg_runtime.bounded_soak.agent0_context import agent0_soak_context
from hg_runtime.bounded_soak.budget import BudgetTracker
from hg_runtime.bounded_soak.receipts import ewj_soak_event, write_soak_receipt
from hg_runtime.bounded_soak.schema import (
    BoundedSoakProfile,
    SoakBudget,
    SoakReceipt,
    SoakRun,
    SoakStopCondition,
    SoakTask,
    SoakTaskResult,
    SoakVerdict,
)
from hg_runtime.bounded_soak.stop_conditions import check_stop
from hg_runtime.bounded_soak.tasks import ALLOWED_TASK_KINDS, default_soak_tasks

_LAZY = {"SupervisorConfig", "run_soak", "status_payload"}


def __getattr__(name: str):
    if name in _LAZY:
        from hg_runtime.bounded_soak.supervisor import SupervisorConfig, run_soak, status_payload

        return {"SupervisorConfig": SupervisorConfig, "run_soak": run_soak, "status_payload": status_payload}[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "ALLOWED_TASK_KINDS",
    "BoundedSoakProfile",
    "BudgetTracker",
    "SoakBudget",
    "SoakReceipt",
    "SoakRun",
    "SoakStopCondition",
    "SoakTask",
    "SoakTaskResult",
    "SoakVerdict",
    "SupervisorConfig",
    "agent0_soak_context",
    "check_stop",
    "default_soak_tasks",
    "ewj_soak_event",
    "run_soak",
    "status_payload",
    "write_soak_receipt",
]
