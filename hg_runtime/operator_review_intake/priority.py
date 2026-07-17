"""ORI deterministic fixture prioritizer — priority is not permission."""

from __future__ import annotations

from hg_core.ori_cluster.errors import ORI_CRITICAL_REVIEW_ESCALATED, ORI_PRIORITY_ASSIGNED, ORI_PRIORITY_NOT_PERMISSION
from hg_core.ori_cluster.no_authority import advisory_only_marker
from hg_core.policy_safety.hashing import canonical_hash
from hg_runtime.operator_review_intake.request_types import (
    CRITICAL_REVIEW_TYPES,
    ItemPriority,
    OperatorReviewItem,
    OperatorReviewRequest,
)


def _deterministic_id(prefix: str, *parts: str) -> str:
    digest = canonical_hash({"prefix": prefix, "parts": list(parts)})
    return f"{prefix}-{digest.rsplit(':', 1)[-1][:12]}"


def _priority_for_request(request: OperatorReviewRequest) -> ItemPriority:
    if request.is_critical():
        return "critical"
    if request.review_type in (
        "publication_review",
        "infrastructure_request",
        "mission_drift",
        "trust_calibration",
        "dependency_attachment",
        "route_conflict",
    ):
        base: ItemPriority = "high"
    elif request.review_type in ("clarification", "context_pruning", "approve_or_reject"):
        base = "normal"
    elif request.urgency == "low":
        base = "low"
    else:
        base = "normal"

    if request.urgency == "critical" and base != "critical":
        return "critical"
    if request.urgency == "high" and base in ("low", "normal"):
        return "high"
    return base


def _visible_actions(request: OperatorReviewRequest) -> tuple[str, ...]:
    actions = ["view", "defer", "request_more_info"]
    if request.requires_explicit_operator_action:
        actions = ["view", "approve_or_reject", "defer", "request_more_info"]
    return tuple(actions)


def _disclosures(request: OperatorReviewRequest) -> tuple[str, ...]:
    disclosures: list[str] = []
    if request.review_type in CRITICAL_REVIEW_TYPES:
        disclosures.append("critical_review")
    if request.reversibility == "irreversible":
        disclosures.append("irreversible_action")
    if request.review_type in ("memory_deletion", "shutdown_or_reset", "destructive_action_warning"):
        disclosures.append("destructive_action_warning")
    return tuple(disclosures)


def prioritize_review_requests(
    requests: tuple[OperatorReviewRequest, ...],
    *,
    canonical_refs: list[str] | None = None,
) -> dict[str, object]:
    allowed = set(canonical_refs) if canonical_refs is not None else {r.review_request_id for r in requests}
    items: list[OperatorReviewItem] = []
    critical_count = 0

    for request in sorted(requests, key=lambda r: r.review_request_id):
        if request.review_request_id not in allowed:
            continue
        priority = _priority_for_request(request)
        if priority == "critical":
            critical_count += 1
        status = "shown" if priority in ("critical", "urgent") else "pending"
        items.append(
            OperatorReviewItem(
                review_item_id=_deterministic_id("ori-item", request.review_request_id),
                request_refs=(request.review_request_id,),
                priority=priority,
                operator_visible_summary=request.summary,
                operator_visible_actions=_visible_actions(request),
                hidden_or_internal_refs=request.evidence_refs,
                required_disclosures=_disclosures(request),
                status=status,  # type: ignore[arg-type]
            )
        )

    reason = ORI_CRITICAL_REVIEW_ESCALATED if critical_count else ORI_PRIORITY_ASSIGNED
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": reason,
        "priority_not_permission": True,
        "reason_code_priority_marker": ORI_PRIORITY_NOT_PERMISSION,
        "items": [item.to_payload() for item in items],
        "critical_count": critical_count,
        "review_is_advisory_only": True,
        "permission_granted": False,
    }


__all__ = ["prioritize_review_requests", "_priority_for_request"]
