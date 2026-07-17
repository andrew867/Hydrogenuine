"""Capability broker — admission boundary without execution."""

from hg_runtime.capability_broker.action_registry import (
    FORBIDDEN_REGISTRY_ACTIONS,
    REGISTRY,
    all_registered_actions,
    get_action,
    is_forbidden_action,
    is_known_action,
    registry_hash,
)
from hg_runtime.capability_broker.audit_log import (
    BrokerAuditLog,
    append_decision_to_audit,
    audit_path_for_run,
    record_from_decision,
)
from hg_runtime.capability_broker.broker import evaluate_turn_intent
from hg_runtime.capability_broker.decision_receipts import (
    DecisionReceipt,
    build_decision_receipt,
    validate_decision_receipt,
)
from hg_runtime.capability_broker.dispatch_plan import (
    DispatchPlan,
    DispatchVerdict,
    create_dispatch_plan,
    validate_dispatch_plan,
)
from hg_runtime.capability_broker.errors import BrokerAuditError, BrokerError, BrokerValidationError
from hg_runtime.capability_broker.policy import load_capability_broker_policy
from hg_runtime.capability_broker.refusals import RESTRICTIVE_OPERATOR_STATES
from hg_runtime.capability_broker.schema import (
    BrokerAuditRecord,
    BrokerDecision,
    BrokerDecisionStatus,
    BrokerRefusalReason,
    BrokerRequest,
    BrokerVerdict,
    CapabilityAction,
    CapabilityPolicy,
    validate_broker_decision,
)

__all__ = [
    "FORBIDDEN_REGISTRY_ACTIONS",
    "REGISTRY",
    "RESTRICTIVE_OPERATOR_STATES",
    "BrokerAuditError",
    "BrokerAuditLog",
    "BrokerAuditRecord",
    "BrokerDecision",
    "BrokerDecisionStatus",
    "BrokerError",
    "BrokerRefusalReason",
    "BrokerRequest",
    "BrokerValidationError",
    "BrokerVerdict",
    "CapabilityAction",
    "CapabilityPolicy",
    "DecisionReceipt",
    "DispatchPlan",
    "DispatchVerdict",
    "all_registered_actions",
    "append_decision_to_audit",
    "audit_path_for_run",
    "build_decision_receipt",
    "create_dispatch_plan",
    "evaluate_turn_intent",
    "get_action",
    "is_forbidden_action",
    "is_known_action",
    "load_capability_broker_policy",
    "record_from_decision",
    "registry_hash",
    "validate_broker_decision",
    "validate_decision_receipt",
    "validate_dispatch_plan",
]
