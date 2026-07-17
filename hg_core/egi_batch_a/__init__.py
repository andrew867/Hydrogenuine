"""EGI Batch A."""

from hg_core.egi_batch_a.checks import EGI_A_SLICES, run_egi_batch_a_checks
from hg_core.egi_batch_a.egi import run_egi_closure_checks
from hg_core.egi_batch_a.gate_runner import run_egi_a_gate, run_egi_gap_checks

__all__ = [
    "EGI_A_SLICES",
    "run_egi_a_gate",
    "run_egi_batch_a_checks",
    "run_egi_closure_checks",
    "run_egi_gap_checks",
]
