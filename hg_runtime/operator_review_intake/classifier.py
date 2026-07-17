"""ORI static intake classifier — review intake is not permission."""

from __future__ import annotations

from hg_core.ori_cluster.config import ori_refuse_authority_conversion
from hg_core.ori_cluster.errors import (
    ORI_AUTHORITY_CONVERSION_CONTAINED,
    ORI_REVIEW_REQUEST_RECORDED,
    ORI_SIGNAL_REFUSED,
    REFUSED_FORBIDDEN_INTAKE,
    REFUSED_ORI_AS_AUTHORITY,
    OriValidationError,
)
from hg_core.ori_cluster.evaluation import resolve_risk_containment
from hg_core.ori_cluster.no_authority import advisory_only_marker
from hg_runtime.operator_review_intake.request_types import (
    DESTRUCTIVE_REVIEW_TYPES,
    OperatorReviewRequest,
    classify_intake_risk,
)

_RISK_REASON = {
    "forbidden_intake": REFUSED_FORBIDDEN_INTAKE,
    "authority_conversion": ORI_AUTHORITY_CONVERSION_CONTAINED,
}
_ADVISORY_CONTAINMENT_WAIVED_ORI = "ori.advisory.containment_waived"


def refuse_ori_intake_as_authority(*, treat_as_authority: bool) -> None:
    if treat_as_authority:
        raise OriValidationError(
            REFUSED_ORI_AS_AUTHORITY,
            "operator review intake cannot become authority",
        )


def classify_review_request(
    request: OperatorReviewRequest,
    *,
    treat_as_authority: bool = False,
) -> dict[str, object]:
    if treat_as_authority:
        refuse_ori_intake_as_authority(treat_as_authority=True)

    risk = classify_intake_risk(request.summary)
    contained = resolve_risk_containment(
        risk=risk,
        risk_reason_map=_RISK_REASON,
        waived_reason_code=_ADVISORY_CONTAINMENT_WAIVED_ORI,
        payload={"review_request_id": request.review_request_id, "review_is_advisory_only": True},
        refuse_for_risk=lambda kind: ori_refuse_authority_conversion()
        if kind == "authority_conversion"
        else True,
    )
    if contained is not None:
        status = "contained" if contained.get("containment_active") else "recorded"
        return {
            **contained,
            "status": status,
            "intake_lane": "refused",
            "request": request.to_payload(),
        }

    if request.source_module == "unknown" and request.review_type == "unknown":
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": ORI_SIGNAL_REFUSED,
            "intake_lane": "refused",
            "review_request_id": request.review_request_id,
            "request": request.to_payload(),
        }

    lane = "operator_review"
    disclosures: list[str] = []
    if request.review_type in DESTRUCTIVE_REVIEW_TYPES:
        disclosures.append("destructive_action_warning")
    if request.requires_explicit_operator_action:
        disclosures.append("explicit_operator_action_required")

    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": ORI_REVIEW_REQUEST_RECORDED,
        "intake_lane": lane,
        "review_request_id": request.review_request_id,
        "source_module": request.source_module,
        "review_type": request.review_type,
        "required_disclosures": disclosures,
        "request": request.to_payload(),
        "review_is_advisory_only": True,
    }


__all__ = ["classify_review_request", "refuse_ori_intake_as_authority"]
