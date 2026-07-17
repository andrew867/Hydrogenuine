"""Batch RIB-A reproduction inheritance boundary."""

from hg_core.rib_batch_a.checks import RIB_A_SLICES, run_rib_batch_a_checks
from hg_core.rib_batch_a.gate_runner import run_rib_a_gate, run_rib_inheritance_checks
from hg_core.rib_batch_a.rib import run_rib_closure_checks

__all__ = [
    "RIB_A_SLICES",
    "run_rib_a_gate",
    "run_rib_batch_a_checks",
    "run_rib_closure_checks",
    "run_rib_inheritance_checks",
]
