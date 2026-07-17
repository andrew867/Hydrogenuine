"""Conversationally minted capability leases (hg.lease.v1).

OSS-core substrate: canonical policy AST, four-store separation, deterministic
evaluation, lifecycle state machine, and GPP composition. Leases never execute
and never mint authority by themselves — execution authority is always a
short-lived GovernedPermit minted through hg_gpp.PermitAuthority.
"""

from hg_lease.policy import (
    CanonicalPolicy,
    FactCondition,
    TimeWindowCondition,
    AllOf,
    AnyOf,
    NotCond,
    NumericLimit,
    condition_from_payload,
    validate_policy,
)
from hg_lease.lease import CapabilityLease, LeaseTransitionError, apply_transition
from hg_lease.stores import (
    ContextRecord,
    ContextStore,
    LeaseStore,
    ReceiptStore,
    SituationFact,
    SituationStore,
)
from hg_lease.evaluator import evaluate
from hg_lease.compiler import compile_draft, ClarificationNeeded
from hg_lease.gpp_bridge import LeaseAuthority, OperatorConfirmation

__all__ = [
    "AllOf",
    "AnyOf",
    "CanonicalPolicy",
    "CapabilityLease",
    "ClarificationNeeded",
    "ContextRecord",
    "ContextStore",
    "FactCondition",
    "LeaseAuthority",
    "LeaseStore",
    "LeaseTransitionError",
    "NotCond",
    "NumericLimit",
    "OperatorConfirmation",
    "ReceiptStore",
    "SituationFact",
    "SituationStore",
    "TimeWindowCondition",
    "apply_transition",
    "compile_draft",
    "condition_from_payload",
    "evaluate",
    "validate_policy",
]
