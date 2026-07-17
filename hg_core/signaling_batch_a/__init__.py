"""Signaling Batch S5-A — SBS, DAC, APC."""

from hg_core.signaling_batch_a.checks import (
    S5_A_SLICES,
    SUPPORTED_SLICES,
    run_all_signaling_batch_a_checks,
    run_signaling_batch_a_checks,
)
from hg_core.signaling_batch_a.gate_runner import SLICE_TEST_TARGETS, run_signaling_gate

__all__ = [
    "S5_A_SLICES",
    "SLICE_TEST_TARGETS",
    "SUPPORTED_SLICES",
    "run_all_signaling_batch_a_checks",
    "run_signaling_batch_a_checks",
    "run_signaling_gate",
]
