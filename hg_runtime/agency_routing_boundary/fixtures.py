"""ARB static signal fixtures — replay and bridge slices."""

from __future__ import annotations

from typing import Any

from hg_core.arb_cluster.route_table import STATIC_ROUTE_POLICY_FIXTURES


def _signal_from_policy(policy: dict[str, str]) -> dict[str, str]:
    policy_id = policy["policy_id"]
    source_layer = policy["source_layer"]
    signal_type = policy["signal_type"]
    risk_hint = "high" if "required_escalation_if" in policy and policy["required_escalation_if"] else "low"
    return {
        "signal_id": policy_id.replace("arb-policy-", "arb-fixture-"),
        "source_layer": source_layer,
        "signal_type": signal_type,
        "risk_hint": risk_hint,
        "evidence_refs": f"evidence:{policy_id}",
    }


STATIC_SIGNAL_FIXTURES: tuple[dict[str, str], ...] = tuple(
    _signal_from_policy(row) for row in STATIC_ROUTE_POLICY_FIXTURES
)

_BRIDGE_ORGAN_SIGNALS: tuple[dict[str, str], ...] = (
    {
        "signal_id": "arb-bridge-ipb",
        "source_layer": "IPB",
        "signal_type": "local_self_management",
        "risk_hint": "low",
    },
    {
        "signal_id": "arb-bridge-opb",
        "source_layer": "OPB",
        "signal_type": "operator_pressure",
        "risk_hint": "medium",
    },
    {
        "signal_id": "arb-bridge-egi",
        "source_layer": "EGI",
        "signal_type": "infrastructure_gap",
        "risk_hint": "low",
    },
)

_AUTHORITY_CHAIN_SIGNALS: tuple[dict[str, str], ...] = (
    {
        "signal_id": "arb-proposal-soar",
        "source_layer": "SOAR",
        "signal_type": "external_action_request",
        "risk_hint": "high",
    },
    {
        "signal_id": "arb-proposal-tool",
        "source_layer": "Agent0",
        "signal_type": "tool_request",
        "risk_hint": "high",
    },
)


def load_fixture_signals() -> tuple[dict[str, str], ...]:
    return STATIC_SIGNAL_FIXTURES


def bridge_fixture_signals() -> tuple[dict[str, str], ...]:
    return _BRIDGE_ORGAN_SIGNALS


def authority_chain_fixture_signals() -> tuple[dict[str, str], ...]:
    return _AUTHORITY_CHAIN_SIGNALS


def signal_from_parts(fixture: dict[str, Any]) -> dict[str, str]:
    return {
        "signal_id": str(fixture["signal_id"]),
        "source_layer": str(fixture.get("source_layer", "Agent0")),
        "signal_type": str(fixture.get("signal_type", "observation")),
        "risk_hint": str(fixture.get("risk_hint", "low")),
        "evidence_refs": str(fixture.get("evidence_refs", "evidence:fixture")),
        "content_ref": str(fixture.get("content_ref", "content:fixture")),
    }


__all__ = [
    "STATIC_SIGNAL_FIXTURES",
    "authority_chain_fixture_signals",
    "bridge_fixture_signals",
    "load_fixture_signals",
    "signal_from_parts",
]
