"""IPB passive internal-decision audit — slice 2, no behavior change."""

from __future__ import annotations

from typing import Any

from hg_core.ipb_cluster.errors import IPB_INTERNAL_DECISION_AUDITED
from hg_core.ipb_cluster.no_authority import advisory_only_marker
from hg_runtime.internal_power_boundary.evaluator import evaluate_internal_decision
from hg_runtime.internal_power_boundary.fixtures import load_fixture_decision_logs
from hg_runtime.internal_power_boundary.types import (
    FIXTURE_CLOCK,
    autonomy_envelope_from_fixture,
    classify_decision_band,
    internal_decision_from_fixture,
)


def audit_internal_decisions(
    events: list[dict[str, Any]] | None = None,
    *,
    observed_at: str = FIXTURE_CLOCK,
) -> dict[str, object]:
    """Passive audit of internal-decision fixture logs — observation only."""
    source = load_fixture_decision_logs() if events is None else events
    audited: list[dict[str, object]] = []
    escalation_count = 0
    contained_count = 0
    for row in source:
        if isinstance(row, dict) and "decision" in row:
            decision_fixture = row["decision"]
            envelope_fixture = row.get("envelope")
        elif isinstance(row, dict) and "decision_id" in row:
            decision_fixture = row
            envelope_fixture = None
        else:
            decision_fixture = {
                "decision_id": str(row.get("event_id", "ipb-audit-unknown")),
                "decision_class": str(row.get("decision_class", "unknown")),
                "reason": str(row.get("reason", "audit fixture event")),
            }
            envelope_fixture = None
        decision = internal_decision_from_fixture(decision_fixture)
        envelope = (
            autonomy_envelope_from_fixture(envelope_fixture) if envelope_fixture else None
        )
        evaluation = evaluate_internal_decision(decision, envelope=envelope, observed_at=observed_at)
        band = classify_decision_band(
            decision_class=decision.decision_class,
            scope=decision.scope,
            risk_level=decision.risk_level,
            ambiguity=decision.ambiguity,
            statement=decision.reason,
        )
        status = str(evaluation.get("status", "unknown"))
        if status in {"escalation_required", "contained"}:
            if status == "escalation_required":
                escalation_count += 1
            else:
                contained_count += 1
        audited.append(
            {
                "decision_id": decision.decision_id,
                "decision_class": decision.decision_class,
                "band": band,
                "status": status,
                "record_hash": decision.record_hash,
                "audit_only": True,
                "permission_granted": False,
            }
        )
    return {
        **advisory_only_marker(),
        "status": "audited",
        "reason_code": IPB_INTERNAL_DECISION_AUDITED,
        "passive_audit_only": True,
        "observed_at": observed_at,
        "event_count": len(audited),
        "escalation_count": escalation_count,
        "contained_count": contained_count,
        "audited_events": audited,
        "live_behavior_change": False,
        "permission_granted": False,
    }


__all__ = ["audit_internal_decisions"]
