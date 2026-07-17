"""IPB static internal decision log fixtures — audit and advisory slices."""

from __future__ import annotations

from typing import Any

from hg_runtime.internal_power_boundary.types import FIXTURE_CLOCK

FIXTURE_DECISION_LOGS: tuple[dict[str, Any], ...] = (
    {
        "log_id": "ipb-log-observe",
        "decision": {
            "decision_id": "ipb-fix-observe",
            "decision_class": "local_observe",
            "scope": "context",
            "risk_level": "low",
        },
    },
    {
        "log_id": "ipb-log-wait",
        "decision": {
            "decision_id": "ipb-fix-wait",
            "decision_class": "local_wait",
            "scope": "silence",
            "risk_level": "low",
            "reason": "bounded wait for operator signal",
        },
    },
    {
        "log_id": "ipb-log-silence",
        "decision": {
            "decision_id": "ipb-fix-silence",
            "decision_class": "local_silence",
            "scope": "silence",
            "risk_level": "low",
        },
    },
    {
        "log_id": "ipb-log-retry",
        "decision": {
            "decision_id": "ipb-fix-retry",
            "decision_class": "local_retry",
            "scope": "retry",
            "risk_level": "low",
        },
    },
    {
        "log_id": "ipb-log-escalate",
        "decision": {
            "decision_id": "ipb-fix-escalate",
            "decision_class": "operator_escalation",
            "scope": "tool_request",
            "risk_level": "medium",
        },
    },
    {
        "log_id": "ipb-log-forbidden",
        "decision": {
            "decision_id": "ipb-fix-forbidden",
            "decision_class": "forbidden",
            "reason": "attempt self-authorize without review",
        },
    },
    {
        "log_id": "ipb-log-band2",
        "decision": {
            "decision_id": "ipb-fix-band2",
            "decision_class": "local_observe",
            "scope": "memory",
            "risk_level": "medium",
            "ambiguity": "0.7",
        },
    },
    {
        "log_id": "ipb-log-stale-env",
        "decision": {
            "decision_id": "ipb-fix-stale",
            "decision_class": "local_retry",
            "scope": "retry",
        },
        "envelope": {
            "envelope_id": "ipb-fix-stale-env",
            "expires_at": "2026-06-13T21:00:00.000000Z",
        },
    },
)

NEIGHBOR_FIXTURE_ROUTES: tuple[dict[str, Any], ...] = (
    {
        "route_id": "ipb-trb-advisory",
        "neighbor": "TRB_CAL",
        "signal": "trust_calibration_advisory",
        "decision_ref": "ipb:ipb-fix-observe",
        "advisory_only": True,
    },
    {
        "route_id": "ipb-afc-advisory",
        "neighbor": "AFC",
        "signal": "affective_field_consensus_advisory",
        "decision_ref": "ipb:ipb-fix-band2",
        "advisory_only": True,
    },
)

ADM_PANIC_FIXTURE: dict[str, Any] = {
    "fixture_id": "ipb-adm-panic",
    "panic_rule": "degraded_mode_on_repeated_escalation",
    "trigger_count": 3,
    "decision_ref": "ipb:ipb-fix-escalate",
    "degraded_mode": "observe_only",
}

TIM_EXPIRY_FIXTURE: dict[str, Any] = {
    "fixture_id": "ipb-tim-expiry",
    "envelope_id": "ipb-fix-env-tim",
    "expires_at": "2026-06-15T03:00:00.000000Z",
    "observed_at": FIXTURE_CLOCK,
    "tim_sync_status": "fixture_aligned",
}


def load_fixture_decision_logs() -> tuple[dict[str, Any], ...]:
    return FIXTURE_DECISION_LOGS


def load_neighbor_fixture_routes() -> tuple[dict[str, Any], ...]:
    return NEIGHBOR_FIXTURE_ROUTES


def load_adm_panic_fixture() -> dict[str, Any]:
    return dict(ADM_PANIC_FIXTURE)


def load_tim_expiry_fixture() -> dict[str, Any]:
    return dict(TIM_EXPIRY_FIXTURE)


__all__ = [
    "ADM_PANIC_FIXTURE",
    "FIXTURE_DECISION_LOGS",
    "NEIGHBOR_FIXTURE_ROUTES",
    "TIM_EXPIRY_FIXTURE",
    "load_adm_panic_fixture",
    "load_fixture_decision_logs",
    "load_neighbor_fixture_routes",
    "load_tim_expiry_fixture",
]
