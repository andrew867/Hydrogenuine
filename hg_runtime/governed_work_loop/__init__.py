"""Governed autonomous work loop for Agent Zero Phase 23."""

from __future__ import annotations

__all__ = [
    "GovernedWorkEnvelope",
    "GovernedWorkLoopPostflight",
    "GovernedWorkLoopVerdict",
    "GovernedWorkReceipt",
    "build_governed_work_loop_monitor_snapshot",
    "create_demo_envelope",
    "load_postflight",
    "run_governed_work_loop_once",
    "run_governed_work_loop_smoke",
]


def __getattr__(name: str):
    if name in {"GovernedWorkLoopVerdict", "load_governed_work_policy"}:
        from hg_runtime.governed_work_loop import schema as _s

        return getattr(_s, name)
    if name in {"GovernedWorkEnvelope", "ExternalActionEnvelope", "create_demo_envelope", "load_work_envelope"}:
        from hg_runtime.governed_work_loop import work_envelope as _we

        return getattr(_we, name)
    if name == "GovernedWorkReceipt":
        from hg_runtime.governed_work_loop.work_receipts import GovernedWorkReceipt

        return GovernedWorkReceipt
    if name in {"run_governed_work_loop_once", "run_governed_work_loop_smoke"}:
        from hg_runtime.governed_work_loop import work_runner as _wr

        return getattr(_wr, name)
    if name in {"GovernedWorkLoopPostflight", "load_postflight"}:
        from hg_runtime.governed_work_loop import postflight as _pf

        return getattr(_pf, name)
    if name == "build_governed_work_loop_monitor_snapshot":
        from hg_runtime.governed_work_loop import exciton_snapshot as _ex

        return getattr(_ex, name)
    raise AttributeError(name)
