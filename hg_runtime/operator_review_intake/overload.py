"""ORI fixture overload detector — overload response is not authority."""

from __future__ import annotations

from hg_core.ori_cluster.errors import ORI_LOW_PRIORITY_DEFERRED, ORI_OPERATOR_OVERLOAD_SIGNAL_RECORDED
from hg_core.ori_cluster.no_authority import advisory_only_marker
from hg_core.policy_safety.hashing import canonical_hash
from hg_runtime.operator_review_intake.request_types import (
    OperatorOverloadSignal,
    OperatorReviewItem,
    OverloadAction,
    OverloadLevel,
)

# Advisory fixture thresholds from ORI_OPERATOR_OVERLOAD_MODEL.md
MILD_REQUEST_THRESHOLD = 5
MILD_DUPLICATE_THRESHOLD = 2
MODERATE_UNRESOLVED_THRESHOLD = 4
MODERATE_INTERRUPT_THRESHOLD = 2
SEVERE_DUPLICATE_WITH_CRITICAL = 3


def _deterministic_id(prefix: str, *parts: str) -> str:
    digest = canonical_hash({"prefix": prefix, "parts": list(parts)})
    return f"{prefix}-{digest.rsplit(':', 1)[-1][:12]}"


def _overload_level(
    *,
    request_count: int,
    interrupt_count: int,
    duplicate_count: int,
    critical_count: int,
    unresolved_count: int,
) -> OverloadLevel:
    if critical_count >= 1 and unresolved_count >= 6:
        return "critical"
    if critical_count >= 1 and duplicate_count >= SEVERE_DUPLICATE_WITH_CRITICAL:
        return "severe"
    if unresolved_count >= MODERATE_UNRESOLVED_THRESHOLD or interrupt_count >= MODERATE_INTERRUPT_THRESHOLD:
        return "moderate"
    if request_count >= MILD_REQUEST_THRESHOLD or duplicate_count >= MILD_DUPLICATE_THRESHOLD:
        return "mild"
    return "none"


def _recommended_action(level: OverloadLevel) -> OverloadAction:
    mapping: dict[OverloadLevel, OverloadAction] = {
        "none": "unknown",
        "mild": "batch_low_priority",
        "moderate": "defer_nonurgent",
        "severe": "escalate_critical_only",
        "critical": "operator_review_of_queue_policy",
        "unknown": "unknown",
    }
    return mapping[level]


def detect_operator_overload(
    *,
    items: list[dict[str, object]],
    request_count: int,
    duplicate_count: int,
    window_start: str,
    window_end: str,
    operator_response_latency: str | None = None,
) -> dict[str, object]:
    critical_count = sum(1 for item in items if item.get("priority") == "critical")
    interrupt_count = sum(1 for item in items if item.get("priority") in ("critical", "urgent"))
    unresolved_count = sum(1 for item in items if item.get("status") in ("pending", "shown", "deferred"))

    level = _overload_level(
        request_count=request_count,
        interrupt_count=interrupt_count,
        duplicate_count=duplicate_count,
        critical_count=critical_count,
        unresolved_count=unresolved_count,
    )
    action = _recommended_action(level)

    signal: OperatorOverloadSignal | None = None
    if level != "none":
        signal = OperatorOverloadSignal(
            overload_signal_id=_deterministic_id("ori-overload", window_start, window_end, level),
            window_start=window_start,
            window_end=window_end,
            request_count=request_count,
            interrupt_count=interrupt_count,
            duplicate_count=duplicate_count,
            critical_count=critical_count,
            unresolved_count=unresolved_count,
            overload_level=level,
            recommended_action=action,
            operator_response_latency=operator_response_latency,
        )

    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": ORI_OPERATOR_OVERLOAD_SIGNAL_RECORDED,
        "overload_level": level,
        "recommended_action": action,
        "overload_signal": signal.to_payload() if signal else None,
        "critical_still_interrupts": critical_count > 0,
        "review_is_advisory_only": True,
    }


def apply_overload_deferrals(
    items: list[OperatorReviewItem],
    *,
    overload_level: str,
) -> dict[str, object]:
    deferred_ids: list[str] = []
    if overload_level in ("moderate", "severe", "critical"):
        for item in items:
            if item.priority == "low" and item.status == "pending":
                deferred_ids.append(item.review_item_id)

    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": ORI_LOW_PRIORITY_DEFERRED if deferred_ids else ORI_OPERATOR_OVERLOAD_SIGNAL_RECORDED,
        "deferred_item_refs": deferred_ids,
        "review_is_advisory_only": True,
    }


__all__ = [
    "MILD_DUPLICATE_THRESHOLD",
    "MILD_REQUEST_THRESHOLD",
    "apply_overload_deferrals",
    "detect_operator_overload",
]
