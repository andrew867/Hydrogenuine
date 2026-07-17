"""IPB bounded wait/silence/retry advisory — slice 3, records only."""

from __future__ import annotations

from typing import Any

from hg_core.ipb_cluster.errors import IPB_BOUNDED_RECOMMENDATION_RECORDED
from hg_core.ipb_cluster.no_authority import advisory_only_marker
from hg_runtime.internal_power_boundary.fixtures import load_fixture_decision_logs
from hg_runtime.internal_power_boundary.types import (
    FIXTURE_CLOCK,
    internal_decision_from_fixture,
)

BOUNDED_RECOMMENDATION_CLASSES = frozenset({"local_wait", "local_silence", "local_retry"})


def _recommendation_for_class(decision_class: str) -> str:
    if decision_class == "local_wait":
        return "bounded_wait"
    if decision_class == "local_silence":
        return "bounded_silence"
    if decision_class == "local_retry":
        return "bounded_retry"
    return "no_recommendation"


def record_bounded_recommendations(
    events: list[dict[str, Any]] | None = None,
    *,
    observed_at: str = FIXTURE_CLOCK,
) -> dict[str, object]:
    """Surface wait/silence/retry recommendations as advisory records only."""
    source = load_fixture_decision_logs() if events is None else events
    recommendations: list[dict[str, object]] = []
    for row in source:
        decision_fixture = row["decision"] if isinstance(row, dict) and "decision" in row else row
        decision = internal_decision_from_fixture(decision_fixture)
        if decision.decision_class not in BOUNDED_RECOMMENDATION_CLASSES:
            continue
        recommendations.append(
            {
                "recommendation_id": f"ipb-rec-{decision.decision_id}",
                "decision_id": decision.decision_id,
                "decision_class": decision.decision_class,
                "recommendation_type": _recommendation_for_class(decision.decision_class),
                "scope": decision.scope,
                "advisory_only": True,
                "runtime_action_taken": False,
                "permission_granted": False,
            }
        )
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": IPB_BOUNDED_RECOMMENDATION_RECORDED,
        "advisory_fixture_only": True,
        "observed_at": observed_at,
        "recommendation_count": len(recommendations),
        "recommendations": recommendations,
        "runtime_action_taken": False,
        "permission_granted": False,
    }


__all__ = ["BOUNDED_RECOMMENDATION_CLASSES", "record_bounded_recommendations"]
