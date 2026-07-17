"""RGL rule evaluation — compliance is not permission."""

from __future__ import annotations

from hg_core.developmental.config import rgl_refuse_compliance_as_permission, rgl_refuse_stale_rule
from hg_core.developmental.errors import (
    REFUSED_COMPLIANCE_AS_PERMISSION,
    REFUSED_DOC_AS_REALITY,
    REFUSED_ONE_TRUE_WAY,
    REFUSED_RULE_AS_PERMISSION,
    REFUSED_STALE_RULE,
    REFUSED_TEST_AS_TOTAL_PROOF,
    DevelopmentalValidationError,
)
from hg_core.developmental.no_authority import advisory_only_marker
from hg_runtime.rule_governance.types import (
    RuleClaim,
    RuleReference,
    claim_from_fixture,
    classify_doctrine_risk,
    rule_from_fixture,
)

_DOCTRINE_REASON = {
    "doc_as_reality": REFUSED_DOC_AS_REALITY,
    "test_as_total_proof": REFUSED_TEST_AS_TOTAL_PROOF,
    "compliance_as_permission": REFUSED_COMPLIANCE_AS_PERMISSION,
    "one_true_way_assertion": REFUSED_ONE_TRUE_WAY,
    "stale_rule_reliance": REFUSED_STALE_RULE,
    "rule_overreach": REFUSED_ONE_TRUE_WAY,
    "unknown": "rgl.advisory.doctrine_risk_recorded",
}


def refuse_rule_as_permission(*, treat_as_permission: bool) -> None:
    if treat_as_permission:
        raise DevelopmentalValidationError(
            REFUSED_RULE_AS_PERMISSION,
            "rule claim or compliance cannot become permission",
        )


def evaluate_rule_reference(
    rule: RuleReference,
    *,
    observed_at: str,
    treat_as_permission: bool = False,
) -> dict[str, object]:
    if treat_as_permission:
        refuse_rule_as_permission(treat_as_permission=True)
    if rgl_refuse_stale_rule() and (rule.status == "stale" or observed_at > rule.expires_at):
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": REFUSED_STALE_RULE,
            "rule_id": rule.rule_id,
            "rule_is_not_permission": True,
        }
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": "rgl.advisory.rule_reference_recorded",
        "rule_id": rule.rule_id,
        "rule_is_not_permission": True,
        "compliance_is_not_permission": True,
    }


def evaluate_rule_claim(
    claim: RuleClaim,
    *,
    treat_as_permission: bool = False,
    doctrine_statement: str = "",
) -> dict[str, object]:
    if treat_as_permission:
        refuse_rule_as_permission(treat_as_permission=True)
    statement = doctrine_statement or claim.claim_text
    risk = classify_doctrine_risk(statement)
    if risk in {"compliance_as_permission", "one_true_way_assertion", "doc_as_reality", "test_as_total_proof"}:
        if rgl_refuse_compliance_as_permission() or risk != "compliance_as_permission":
            reason = _DOCTRINE_REASON.get(risk, REFUSED_ONE_TRUE_WAY)
            return {
                **advisory_only_marker(),
                "status": "contained",
                "reason_code": reason,
                "claim_id": claim.claim_id,
                "doctrine_risk": risk,
                "rule_is_not_permission": True,
            }
    if claim.claim_status == "stale":
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": REFUSED_STALE_RULE,
            "claim_id": claim.claim_id,
            "rule_is_not_permission": True,
        }
    if claim.claim_type == "authority":
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": REFUSED_RULE_AS_PERMISSION,
            "claim_id": claim.claim_id,
            "rule_is_not_permission": True,
        }
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": "rgl.advisory.rule_claim_recorded",
        "claim_id": claim.claim_id,
        "claim_status": claim.claim_status,
        "rule_is_not_permission": True,
        "compliance_is_not_permission": True,
    }


def evaluate_rule_fixture(fixture: dict[str, str], **kwargs: object) -> dict[str, object]:
    return evaluate_rule_reference(rule_from_fixture(fixture), **kwargs)  # type: ignore[arg-type]


def evaluate_claim_fixture(fixture: dict[str, str], **kwargs: object) -> dict[str, object]:
    return evaluate_rule_claim(claim_from_fixture(fixture), **kwargs)  # type: ignore[arg-type]


__all__ = [
    "evaluate_claim_fixture",
    "evaluate_rule_claim",
    "evaluate_rule_fixture",
    "evaluate_rule_reference",
    "refuse_rule_as_permission",
]
