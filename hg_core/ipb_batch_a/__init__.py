"""IPB Batch A — internal power boundary first safe slice."""

from hg_core.ipb_batch_a.checks import IPB_A_SLICES, run_ipb_batch_a_checks
from hg_core.ipb_batch_a.gate_runner import run_ipb_a_gate

__all__ = ["IPB_A_SLICES", "run_ipb_a_gate", "run_ipb_batch_a_checks"]
