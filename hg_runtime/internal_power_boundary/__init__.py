"""IPB runtime — local autonomy is not permission."""

from hg_runtime.internal_power_boundary.advisory import record_bounded_recommendations
from hg_runtime.internal_power_boundary.audit import audit_internal_decisions
from hg_runtime.internal_power_boundary.evaluator import (
    analyze_fixture_bundle,
    evaluate_escalation_decision,
    evaluate_internal_decision,
    evaluate_learning_record,
    evaluate_self_bound_rule,
    refuse_ipb_as_authority,
)
from hg_runtime.internal_power_boundary.fixtures import load_fixture_decision_logs
from hg_runtime.internal_power_boundary.neighbor_integration import integrate_neighbor_fixture_routes
from hg_runtime.internal_power_boundary.proposal import (
    dispatch_local_decision_proposal,
    refuse_ipb_proposal_as_permission,
)
from hg_runtime.internal_power_boundary.types import (
    FIXTURE_CLOCK,
    IPB_SCHEMA_VERSION,
    AutonomyEnvelope,
    EscalationDecision,
    InternalDecision,
    SelfBoundLearningRecord,
    SelfBoundRule,
    autonomy_envelope_from_fixture,
    classify_decision_band,
    classify_ipb_risk,
    escalation_decision_from_fixture,
    internal_decision_from_fixture,
    learning_record_from_fixture,
    self_bound_rule_from_fixture,
)

__all__ = [
    "FIXTURE_CLOCK",
    "IPB_SCHEMA_VERSION",
    "AutonomyEnvelope",
    "EscalationDecision",
    "InternalDecision",
    "SelfBoundLearningRecord",
    "SelfBoundRule",
    "analyze_fixture_bundle",
    "audit_internal_decisions",
    "autonomy_envelope_from_fixture",
    "classify_decision_band",
    "classify_ipb_risk",
    "dispatch_local_decision_proposal",
    "escalation_decision_from_fixture",
    "evaluate_escalation_decision",
    "evaluate_internal_decision",
    "evaluate_learning_record",
    "evaluate_self_bound_rule",
    "integrate_neighbor_fixture_routes",
    "internal_decision_from_fixture",
    "learning_record_from_fixture",
    "load_fixture_decision_logs",
    "record_bounded_recommendations",
    "refuse_ipb_as_authority",
    "refuse_ipb_proposal_as_permission",
    "self_bound_rule_from_fixture",
]
