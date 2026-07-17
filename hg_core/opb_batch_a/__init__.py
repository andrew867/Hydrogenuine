"""OPB Batch A — operator power boundary first safe slice."""

from hg_core.opb_batch_a.checks import OPB_A_SLICES, run_opb_batch_a_checks
from hg_core.opb_batch_a.gate_runner import run_opb_a_gate

__all__ = ["OPB_A_SLICES", "run_opb_a_gate", "run_opb_batch_a_checks"]
