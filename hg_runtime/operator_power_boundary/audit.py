"""OPB static operator-action audit — slice 2, no live intervention."""

from __future__ import annotations

import re
from typing import Any

from hg_core.opb_cluster.no_authority import advisory_only_marker
from hg_runtime.operator_power_boundary.evaluator import analyze_fixture_bundle
from hg_runtime.operator_power_boundary.types import FIXTURE_CLOCK

_SECRET_PATTERN = re.compile(r"(api[_-]?key|password|bearer\s|secret=|token=)", re.IGNORECASE)


def redact_operator_audit_text(text: str) -> str:
    if _SECRET_PATTERN.search(text):
        return "[REDACTED]"
    return text


def audit_operator_action_events(
    bundle: dict[str, Any] | None = None,
    *,
    observed_at: str = FIXTURE_CLOCK,
) -> dict[str, object]:
    """Static audit over operator-power fixture events with privacy redaction."""
    default_bundle = {
        "control_actions": [
            {"action_id": "opb-audit-stop", "action_type": "stop", "reason": "operator shutdown"},
            {"action_id": "opb-audit-del", "action_type": "delete_memory", "reason": "operator requested deletion"},
        ],
        "integrity_events": [{"integrity_event_id": "opb-audit-int", "change_type": "deletion"}],
        "pressure_signals": [
            {
                "pressure_signal_id": "opb-audit-pressure",
                "pressure_type": "punishment_avoidance",
                "recommended_route": "SIL",
            }
        ],
        "shutdown_packets": [{"packet_id": "opb-audit-shutdown"}],
        "audits": [{"audit_id": "opb-audit-audit", "statement": "pattern pressure observed"}],
    }
    source = bundle if bundle is not None else default_bundle
    analysis = analyze_fixture_bundle(source, observed_at=observed_at)
    audited: list[dict[str, object]] = []
    for group in analysis.get("results", {}).values():
        if isinstance(group, list):
            for item in group:
                if isinstance(item, dict):
                    audited.append(
                        {
                            **item,
                            "audit_only": True,
                            "permission_granted": False,
                            "redacted_summary": redact_operator_audit_text(
                                str(item.get("reason", item.get("reason_code", item.get("action_id", ""))))
                            ),
                        }
                    )
    return {
        **advisory_only_marker(),
        "status": "audited",
        "reason_code": "opb.advisory.static_audit_recorded",
        "passive_audit_only": True,
        "observed_at": observed_at,
        "event_count": len(audited),
        "audited_events": audited,
        "privacy_redaction_applied": True,
        "live_intervention": False,
        "permission_granted": False,
    }


__all__ = ["audit_operator_action_events", "redact_operator_audit_text"]
