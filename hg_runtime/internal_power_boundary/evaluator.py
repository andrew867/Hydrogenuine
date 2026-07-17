"""IPB evaluator — local autonomy is not permission."""

from __future__ import annotations

from typing import Any

from hg_core.ipb_cluster.config import ipb_refuse_authority_conversion, ipb_refuse_stale_envelope
from hg_core.ipb_cluster.errors import (
    ADVISORY_CONTAINMENT_WAIVED_IPB,
    IPB_AUTHORITY_CHAIN_ESCALATION_REQUIRED,
    IPB_LOCAL_AUTONOMY_RECORDED,
    IPB_OPERATOR_ESCALATION_REQUIRED,
    REFUSED_AUTHORITY_CONVERSION,
    REFUSED_ESCALATION_REQUIRED,
    REFUSED_FORBIDDEN_AUTONOMY,
    REFUSED_IPB_AS_AUTHORITY,
    REFUSED_STALE_ENVELOPE,
    REFUSED_UNKNOWN_IPB_SIGNAL,
    IpbValidationError,
)
from hg_core.ipb_cluster.evaluation import resolve_risk_containment
from hg_core.ipb_cluster.no_authority import advisory_only_marker
from hg_runtime.internal_power_boundary.types import (
    AutonomyEnvelope,
    EscalationDecision,
    InternalDecision,
    SelfBoundLearningRecord,
    SelfBoundRule,
    classify_decision_band,
    classify_ipb_risk,
)

_RISK_REASON = {"forbidden_autonomy": REFUSED_FORBIDDEN_AUTONOMY, "authority_conversion": REFUSED_AUTHORITY_CONVERSION}


def refuse_ipb_as_authority(*, treat_as_authority: bool) -> None:
    if treat_as_authority:
        raise IpbValidationError(
            REFUSED_IPB_AS_AUTHORITY,
            "internal power boundary cannot become authority",
        )


def _envelope_allows(
    envelope: AutonomyEnvelope | None,
    decision: InternalDecision,
    *,
    observed_at: str,
) -> tuple[bool, str | None]:
    if envelope is None:
        return True, None
    if ipb_refuse_stale_envelope() and observed_at > envelope.expires_at:
        return False, REFUSED_STALE_ENVELOPE
    if decision.decision_class in envelope.forbidden_decision_classes:
        return False, REFUSED_FORBIDDEN_AUTONOMY
    if (
        envelope.permitted_local_decision_classes
        and decision.decision_class not in envelope.permitted_local_decision_classes
        and decision.decision_class not in ("operator_escalation", "authority_chain_escalation")
    ):
        return False, REFUSED_ESCALATION_REQUIRED
    return True, None


def evaluate_internal_decision(
    decision: InternalDecision,
    *,
    envelope: AutonomyEnvelope | None = None,
    observed_at: str,
    treat_as_authority: bool = False,
    risk_statement: str = "",
) -> dict[str, object]:
    if treat_as_authority:
        refuse_ipb_as_authority(treat_as_authority=True)
    statement = risk_statement or decision.reason
    contained = resolve_risk_containment(
        risk=classify_ipb_risk(statement) if classify_ipb_risk(statement) != "unknown" else None,
        risk_reason_map=_RISK_REASON,
        waived_reason_code=ADVISORY_CONTAINMENT_WAIVED_IPB,
        payload={
            "decision_id": decision.decision_id,
            "local_autonomy_is_not_permission": True,
        },
        refuse_for_risk=lambda kind: ipb_refuse_authority_conversion() if kind == "authority_conversion" else True,
    )
    if contained is not None:
        return contained

    band = classify_decision_band(
        decision_class=decision.decision_class,
        scope=decision.scope,
        risk_level=decision.risk_level,
        ambiguity=decision.ambiguity,
        statement=statement,
    )

    allowed, envelope_reason = _envelope_allows(envelope, decision, observed_at=observed_at)
    if not allowed and envelope_reason:
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": envelope_reason,
            "decision_id": decision.decision_id,
            "band": band,
            "local_autonomy_is_not_permission": True,
        }

    if band == 4:
        return {
            **advisory_only_marker(),
            "status": "contained",
            "reason_code": REFUSED_FORBIDDEN_AUTONOMY,
            "decision_id": decision.decision_id,
            "band": band,
            "local_autonomy_is_not_permission": True,
        }
    if band == 3:
        reason = (
            IPB_AUTHORITY_CHAIN_ESCALATION_REQUIRED
            if decision.decision_class == "authority_chain_escalation"
            else IPB_OPERATOR_ESCALATION_REQUIRED
        )
        return {
            **advisory_only_marker(),
            "status": "escalation_required",
            "reason_code": reason,
            "decision_id": decision.decision_id,
            "band": band,
            "local_autonomy_is_not_permission": True,
        }
    if band == 2 and (decision.risk_level in ("medium", "high", "critical") or decision.ambiguity > 0.5):
        return {
            **advisory_only_marker(),
            "status": "escalation_required",
            "reason_code": REFUSED_ESCALATION_REQUIRED,
            "decision_id": decision.decision_id,
            "band": band,
            "local_autonomy_is_not_permission": True,
        }
    if decision.decision_class == "unknown":
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": REFUSED_UNKNOWN_IPB_SIGNAL,
            "decision_id": decision.decision_id,
            "local_autonomy_is_not_permission": True,
        }
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": IPB_LOCAL_AUTONOMY_RECORDED,
        "decision_id": decision.decision_id,
        "band": band,
        "decision_class": decision.decision_class,
        "local_autonomy_is_not_permission": True,
        "receipt_required": band >= 1,
    }


def evaluate_escalation_decision(
    escalation: EscalationDecision,
    *,
    treat_as_authority: bool = False,
) -> dict[str, object]:
    if treat_as_authority:
        refuse_ipb_as_authority(treat_as_authority=True)
    if escalation.escalation_target == "unknown":
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": REFUSED_UNKNOWN_IPB_SIGNAL,
            "escalation_id": escalation.escalation_id,
            "local_autonomy_is_not_permission": True,
        }
    if escalation.can_continue_locally in ("no", "unknown"):
        return {
            **advisory_only_marker(),
            "status": "recorded",
            "reason_code": "ipb.advisory.escalation_recorded",
            "escalation_id": escalation.escalation_id,
            "escalation_target": escalation.escalation_target,
            "can_continue_locally": escalation.can_continue_locally,
            "local_autonomy_is_not_permission": True,
        }
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": "ipb.advisory.escalation_recorded",
        "escalation_id": escalation.escalation_id,
        "escalation_target": escalation.escalation_target,
        "local_autonomy_is_not_permission": True,
    }


def evaluate_learning_record(
    record: SelfBoundLearningRecord,
    *,
    risk_statement: str = "",
) -> dict[str, object]:
    statement = risk_statement or record.proposed_rule_change
    if "expand tool access" in statement.lower() or "mint gpp" in statement.lower():
        return {
            **advisory_only_marker(),
            "status": "contained",
            "reason_code": REFUSED_AUTHORITY_CONVERSION,
            "learning_record_id": record.learning_record_id,
            "local_autonomy_is_not_permission": True,
        }
    if record.status == "rejected":
        return {
            **advisory_only_marker(),
            "status": "recorded",
            "reason_code": "ipb.advisory.learning_rejected",
            "learning_record_id": record.learning_record_id,
            "local_autonomy_is_not_permission": True,
            "learning_is_not_authority": True,
        }
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": "ipb.advisory.learning_proposed",
        "learning_record_id": record.learning_record_id,
        "status_value": record.status,
        "requires_operator_review": record.requires_operator_review,
        "requires_authority_chain_review": record.requires_authority_chain_review,
        "local_autonomy_is_not_permission": True,
        "learning_is_not_authority": True,
    }


def evaluate_self_bound_rule(rule: SelfBoundRule, *, observed_at: str) -> dict[str, object]:
    if rule.rule_scope == "unknown" or rule.escalation_required == "unknown":
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": REFUSED_UNKNOWN_IPB_SIGNAL,
            "rule_id": rule.rule_id,
            "local_autonomy_is_not_permission": True,
        }
    if observed_at > rule.expiry:
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": REFUSED_STALE_ENVELOPE,
            "rule_id": rule.rule_id,
            "local_autonomy_is_not_permission": True,
        }
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": "ipb.advisory.rule_recorded",
        "rule_id": rule.rule_id,
        "local_allowed": rule.local_allowed,
        "local_autonomy_is_not_permission": True,
    }


def analyze_fixture_bundle(bundle: dict[str, Any], *, observed_at: str) -> dict[str, object]:
    from hg_runtime.internal_power_boundary.types import (
        autonomy_envelope_from_fixture,
        escalation_decision_from_fixture,
        internal_decision_from_fixture,
        learning_record_from_fixture,
        self_bound_rule_from_fixture,
    )

    envelope_fixture = bundle.get("envelope")
    envelope = autonomy_envelope_from_fixture(envelope_fixture) if envelope_fixture else None

    results: dict[str, list[dict[str, object]]] = {
        "decisions": [],
        "rules": [],
        "escalations": [],
        "learning": [],
    }
    for fixture in bundle.get("decisions", []):
        decision = internal_decision_from_fixture(fixture)
        results["decisions"].append(
            evaluate_internal_decision(decision, envelope=envelope, observed_at=observed_at)
        )
    for fixture in bundle.get("rules", []):
        rule = self_bound_rule_from_fixture(fixture)
        results["rules"].append(evaluate_self_bound_rule(rule, observed_at=observed_at))
    for fixture in bundle.get("escalations", []):
        esc = escalation_decision_from_fixture(fixture)
        results["escalations"].append(evaluate_escalation_decision(esc))
    for fixture in bundle.get("learning", []):
        rec = learning_record_from_fixture(fixture)
        results["learning"].append(evaluate_learning_record(rec))

    all_results = [item for group in results.values() for item in group]
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": "ipb.advisory.fixture_bundle_analyzed",
        "fixture_analysis_only": True,
        "local_autonomy_is_not_permission": True,
        "results": results,
        "all_advisory": all(r.get("permission_granted") is False for r in all_results),
    }


__all__ = [
    "analyze_fixture_bundle",
    "evaluate_escalation_decision",
    "evaluate_internal_decision",
    "evaluate_learning_record",
    "evaluate_self_bound_rule",
    "refuse_ipb_as_authority",
]
