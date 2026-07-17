"""
OS Post-Phase 5: Verification robustness — sources, checks, robustness scoring.
Pack 1: VerificationGraph and verification gate. Pack 5: Verifier economics, correlation.
"""

from .robustness import (
    register_verification_source,
    perform_verification_check,
    compute_robustness_for_action,
    record_verification_insufficient,
    get_robustness_score,
)
from .graph import get_verification_graph, check_verification_gate
from .econ import (
    get_verifier_price,
    update_verifier_price,
    init_verification_budget,
    get_verification_budget_status,
    debit_verification_budget,
    select_verifier_set,
    select_verifier_set_and_debit,
)
from .correlation import (
    compute_correlation,
    emit_correlation_computed,
    update_clusters_and_emit,
    check_monoculture,
    emit_monoculture_detected,
)

__all__ = [
    "register_verification_source",
    "perform_verification_check",
    "compute_robustness_for_action",
    "record_verification_insufficient",
    "get_robustness_score",
    "get_verification_graph",
    "check_verification_gate",
    "get_verifier_price",
    "update_verifier_price",
    "init_verification_budget",
    "get_verification_budget_status",
    "debit_verification_budget",
    "select_verifier_set",
    "select_verifier_set_and_debit",
    "compute_correlation",
    "emit_correlation_computed",
    "update_clusters_and_emit",
    "check_monoculture",
    "emit_monoculture_detected",
]
