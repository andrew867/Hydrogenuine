"""Batch ORI-A closure checks."""

from hg_core.ori_batch_a.checks import (
    ORI_A_SLICES,
    SUPPORTED_SLICES,
    run_all_ori_batch_a_checks,
    run_ori_batch_a_checks,
)
from hg_core.ori_batch_a.gate_runner import SLICE_TEST_TARGETS, run_ori_a_gate, run_ori_intake_checks
from hg_core.ori_batch_a.ori import run_ori_closure_checks

__all__ = [
    "ORI_A_SLICES",
    "SLICE_TEST_TARGETS",
    "SUPPORTED_SLICES",
    "run_all_ori_batch_a_checks",
    "run_ori_a_gate",
    "run_ori_batch_a_checks",
    "run_ori_closure_checks",
    "run_ori_intake_checks",
]
