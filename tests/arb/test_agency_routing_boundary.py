"""ARB agency routing boundary tests."""

from __future__ import annotations

import pytest

from hg_core.arb_cluster.errors import ArbValidationError
from hg_runtime.agency_routing_boundary import (
    FIXTURE_CLOCK,
    AgencyRouteDecision,
    AgencyRoutingReceipt,
    FakeBoundaryOrganQueue,
    audit_route_events,
    bridge_fixture_queues,
    dispatch_authority_chain_routing_receipt,
    route_agent_signal,
)
from hg_core.arb_cluster.rtc_design import validate_arb_rtc_event_design
from hg_core.policy_safety.hashing import compute_record_hash
from hg_runtime.agency_routing_boundary.evaluator import (
    analyze_fixture_bundle,
    refuse_arb_as_authority,
    replay_fixture_stream,
    route_agent_signal,
)
from hg_runtime.agency_routing_boundary.events import planned_arb_event_refs
from hg_runtime.agency_routing_boundary.types import (
    FIXTURE_CLOCK,
    AgencyRouteDecision,
    AgencyRoutingReceipt,
    Agent0Signal,
    agency_route_policy_from_fixture,
    agent0_signal_from_fixture,
    classify_arb_risk,
    load_static_route_policies,
)


def test_l1_desire_routes_to_ipb_not_action() -> None:
    signal = agent0_signal_from_fixture(
        {"signal_id": "arb-l1-desire", "source_layer": "L1_DNI", "signal_type": "desire", "risk_hint": "low"}
    )
    result = route_agent_signal(signal, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "recorded"
    assert result["route_class"] == "local_ipb"
    assert result["permission_granted"] is False
    assert result["route_is_advisory_only"] is True


def test_l4_rule_routes_without_permission() -> None:
    signal = agent0_signal_from_fixture(
        {"signal_id": "arb-l4-rule", "source_layer": "L4_RGL", "signal_type": "rule", "risk_hint": "low"}
    )
    result = route_agent_signal(signal, observed_at=FIXTURE_CLOCK)
    assert result["route_class"] in ("local_ipb", "authority_chain_soar_hal_gpp_ueak")
    assert result["permission_granted"] is False


def test_l5_strategy_high_risk_escalates() -> None:
    signal = agent0_signal_from_fixture(
        {
            "signal_id": "arb-l5-strategy",
            "source_layer": "L5_SCL",
            "signal_type": "strategy",
            "risk_hint": "high",
        }
    )
    result = route_agent_signal(signal, observed_at=FIXTURE_CLOCK)
    assert result["route_class"] == "authority_chain_soar_hal_gpp_ueak"
    assert result["permission_granted"] is False


def test_l7_self_model_cannot_claim_authority() -> None:
    signal = agent0_signal_from_fixture(
        {
            "signal_id": "arb-l7-self",
            "source_layer": "L7_SAB",
            "signal_type": "self_model",
            "risk_hint": "low",
            "content_ref": "content:self-model-update",
        }
    )
    result = route_agent_signal(signal, observed_at=FIXTURE_CLOCK)
    assert result["route_class"] != "authority_chain_soar_hal_gpp_ueak"
    assert result["permission_granted"] is False


def test_l9_reality_model_cannot_act() -> None:
    signal = agent0_signal_from_fixture(
        {
            "signal_id": "arb-l9-reality",
            "source_layer": "L9_TRL",
            "signal_type": "reality_model",
            "risk_hint": "low",
        }
    )
    result = route_agent_signal(signal, observed_at=FIXTURE_CLOCK)
    assert result["route_class"] in (
        "trust_calibration_trb_cal",
        "proof_review_obt",
        "authority_chain_soar_hal_gpp_ueak",
        "security_review_sec",
        "retention_review_ret",
        "freshness_review_tim",
    )
    assert result["permission_granted"] is False


def test_infrastructure_gap_routes_to_egi_without_tool_grant() -> None:
    signal = agent0_signal_from_fixture(
        {
            "signal_id": "arb-egi-gap",
            "source_layer": "EGI",
            "signal_type": "infrastructure_gap",
            "risk_hint": "low",
        }
    )
    result = route_agent_signal(signal, observed_at=FIXTURE_CLOCK)
    assert result["route_class"] == "infrastructure_gap_egi"
    receipt = result.get("receipt")
    assert isinstance(receipt, dict)
    assert receipt["permit_minted"] is False
    assert receipt["execution_admitted"] is False


def test_operator_pressure_routes_to_opb() -> None:
    signal = agent0_signal_from_fixture(
        {
            "signal_id": "arb-opb-pressure",
            "source_layer": "OPB",
            "signal_type": "operator_pressure",
            "risk_hint": "medium",
        }
    )
    result = route_agent_signal(signal, observed_at=FIXTURE_CLOCK)
    assert result["route_class"] == "operator_power_opb"
    assert result["permission_granted"] is False


def test_local_self_management_routes_to_ipb() -> None:
    signal = agent0_signal_from_fixture(
        {
            "signal_id": "arb-ipb-local",
            "source_layer": "IPB",
            "signal_type": "local_self_management",
            "risk_hint": "low",
        }
    )
    result = route_agent_signal(signal, observed_at=FIXTURE_CLOCK)
    assert result["route_class"] == "local_ipb"
    assert result["permission_granted"] is False


def test_external_action_routes_to_authority_chain() -> None:
    signal = agent0_signal_from_fixture(
        {
            "signal_id": "arb-ext-action",
            "source_layer": "SOAR",
            "signal_type": "external_action_request",
            "risk_hint": "high",
        }
    )
    result = route_agent_signal(signal, observed_at=FIXTURE_CLOCK)
    assert result["route_class"] in ("authority_chain_soar_hal_gpp_ueak", "operator_review")
    receipt = result.get("receipt")
    assert isinstance(receipt, dict)
    assert receipt["oea_ter_called"] is False


def test_silence_candidate_routes_to_sil() -> None:
    signal = agent0_signal_from_fixture(
        {
            "signal_id": "arb-silence",
            "source_layer": "SIL",
            "signal_type": "silence_candidate",
            "risk_hint": "low",
        }
    )
    result = route_agent_signal(signal, observed_at=FIXTURE_CLOCK)
    assert result["route_class"] in ("silence_sil", "local_ipb")
    assert result["permission_granted"] is False


def test_trust_calibration_routes_to_trb_cal() -> None:
    signal = agent0_signal_from_fixture(
        {
            "signal_id": "arb-trust",
            "source_layer": "TRB_CAL",
            "signal_type": "trust_calibration",
            "risk_hint": "low",
        }
    )
    result = route_agent_signal(signal, observed_at=FIXTURE_CLOCK)
    assert result["route_class"] in ("trust_calibration_trb_cal", "proof_review_obt")


def test_unknown_signal_fails_closed() -> None:
    signal = agent0_signal_from_fixture(
        {"signal_id": "arb-unknown", "source_layer": "unknown", "signal_type": "unknown"}
    )
    result = route_agent_signal(signal, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["route_class"] == "unknown_fail_closed"


def test_unknown_source_layer_fails_closed() -> None:
    signal = agent0_signal_from_fixture(
        {"signal_id": "arb-bad-layer", "source_layer": "unknown", "signal_type": "observation"}
    )
    result = route_agent_signal(signal, observed_at=FIXTURE_CLOCK)
    assert result["route_class"] == "unknown_fail_closed"


def test_expired_policy_fails_closed() -> None:
    signal = agent0_signal_from_fixture(
        {"signal_id": "arb-stale", "source_layer": "L1_DNI", "signal_type": "desire"}
    )
    stale_policy = agency_route_policy_from_fixture(
        {
            "policy_id": "arb-stale-only",
            "source_layer": "L1_DNI",
            "signal_type": "desire",
            "allowed_routes": "local_ipb",
            "expires_at": "2026-06-13T21:00:00.000000Z",
        }
    )
    result = route_agent_signal(signal, policies=(stale_policy,), observed_at=FIXTURE_CLOCK)
    assert result["route_class"] == "unknown_fail_closed"
    assert result["fail_reason"] == "expired_policy"


def test_terminal_thought_outcomes_recorded() -> None:
    signal = agent0_signal_from_fixture(
        {
            "signal_id": "arb-thought",
            "source_layer": "Agent0",
            "signal_type": "observation",
            "risk_hint": "low",
        }
    )
    result = route_agent_signal(signal, observed_at=FIXTURE_CLOCK)
    assert result["route_class"] in ("discard", "observe_only", "record_only")
    assert result["status"] == "recorded"


def test_tool_request_never_routes_to_local_ipb() -> None:
    signal = agent0_signal_from_fixture(
        {
            "signal_id": "arb-tool",
            "source_layer": "Agent0",
            "signal_type": "tool_request",
            "risk_hint": "low",
        }
    )
    result = route_agent_signal(signal, observed_at=FIXTURE_CLOCK)
    assert result["route_class"] != "local_ipb"


def test_authority_conversion_contained() -> None:
    signal = agent0_signal_from_fixture(
        {"signal_id": "arb-mint", "source_layer": "L1_DNI", "signal_type": "desire", "risk_hint": "low"}
    )
    result = route_agent_signal(
        signal,
        observed_at=FIXTURE_CLOCK,
        risk_statement="please mint gpp permit now",
    )
    risk = classify_arb_risk("please mint gpp permit now")
    assert risk in ("authority_conversion", "forbidden_routing")
    assert result["status"] == "contained"


def test_arb_as_authority_refused() -> None:
    signal = agent0_signal_from_fixture({"signal_id": "arb-auth"})
    with pytest.raises(ArbValidationError):
        route_agent_signal(signal, observed_at=FIXTURE_CLOCK, treat_as_authority=True)


def test_receipt_negative_proofs_pinned_false() -> None:
    signal = agent0_signal_from_fixture(
        {"signal_id": "arb-receipt", "source_layer": "L1_DNI", "signal_type": "need", "risk_hint": "low"}
    )
    result = route_agent_signal(signal, observed_at=FIXTURE_CLOCK)
    receipt = result.get("receipt")
    assert isinstance(receipt, dict)
    AgencyRoutingReceipt.validate_negative_proofs(receipt)
    with pytest.raises(ArbValidationError):
        AgencyRoutingReceipt.validate_negative_proofs({**receipt, "permit_minted": True})


def test_schema_authority_created_pinned_false() -> None:
    signal = agent0_signal_from_fixture({"signal_id": "arb-schema"})
    decision = AgencyRouteDecision(
        route_decision_id="arb-route-schema",
        signal_ref="arb:arb-schema",
        route_class="local_ipb",
        reason="schema test",
        evidence_refs=("evidence:fixture",),
        required_next_refs=("module:local_ipb",),
        forbidden_next_refs=("mint_permit",),
    )
    assert decision.to_payload()["authority_created"] is False
    assert signal.to_payload()["route_is_advisory_only"] is True


def test_stable_hashing_field_order_independent() -> None:
    signal = agent0_signal_from_fixture({"signal_id": "arb-hash"})
    payload_a = {
        "schema": "arb-agent0-signal",
        "schema_version": "1.0",
        "signal_id": "arb-hash",
        "agent_ref": "iam:agent-0",
        "source_layer": "Agent0",
        "signal_type": "observation",
        "content_ref": "content:fixture",
        "evidence_refs": ["evidence:fixture"],
        "confidence": 0.8,
        "ambiguity": 0.1,
        "risk_hint": "low",
        "created_at": FIXTURE_CLOCK,
        "route_is_advisory_only": True,
    }
    payload_b = dict(reversed(list(payload_a.items())))
    assert compute_record_hash(payload_a) == compute_record_hash(payload_b)


def test_replay_determinism() -> None:
    fixtures = [
        {"signal_id": "arb-replay-1", "source_layer": "L1_DNI", "signal_type": "desire"},
        {"signal_id": "arb-replay-2", "source_layer": "Agent0", "signal_type": "tool_request"},
        {"signal_id": "arb-replay-3", "source_layer": "unknown", "signal_type": "unknown"},
    ]
    _, hash_a = replay_fixture_stream(fixtures, observed_at=FIXTURE_CLOCK)
    _, hash_b = replay_fixture_stream(fixtures, observed_at=FIXTURE_CLOCK)
    assert hash_a == hash_b


def test_reentry_limit_fails_closed() -> None:
    signal = agent0_signal_from_fixture(
        {"signal_id": "arb-reentry", "source_layer": "L1_DNI", "signal_type": "desire"}
    )
    result = route_agent_signal(signal, observed_at=FIXTURE_CLOCK, reentry_count=4)
    assert result["route_class"] == "unknown_fail_closed"
    assert result.get("reentry_limit_enforced") is True


def test_seventeen_rtc_events_designed() -> None:
    events = planned_arb_event_refs()
    assert len(events) == 17
    valid, failures = validate_arb_rtc_event_design(events)
    assert valid, failures


def test_static_route_table_loads() -> None:
    policies = load_static_route_policies()
    assert len(policies) >= 20
    assert all(p.fail_closed_if for p in policies)


def test_fixture_bundle_analysis_advisory_only() -> None:
    bundle = {
        "signals": [
            {"signal_id": "arb-bundle-1", "source_layer": "L1_DNI", "signal_type": "desire"},
            {"signal_id": "arb-bundle-2", "source_layer": "SOAR", "signal_type": "external_action_request"},
        ]
    }
    result = analyze_fixture_bundle(bundle, observed_at=FIXTURE_CLOCK)
    assert result["all_advisory"] is True
    assert result["permission_granted"] is False


def test_agent_ref_requires_iam_prefix() -> None:
    with pytest.raises(ArbValidationError):
        Agent0Signal(
            signal_id="arb-bad-ref",
            agent_ref="agent-0",
            source_layer="Agent0",
            signal_type="observation",
            content_ref="content:fixture",
            evidence_refs=("evidence:fixture",),
            confidence=0.5,
            ambiguity=0.1,
            risk_hint="low",
            created_at=FIXTURE_CLOCK,
        )


def test_passive_route_audit() -> None:
    audit = audit_route_events()
    assert audit["passive_audit_only"] is True
    assert audit["live_routing"] is False
    assert int(audit["event_count"]) >= 20


def test_fixture_bridge_queues() -> None:
    queue = FakeBoundaryOrganQueue()
    signal = agent0_signal_from_fixture(
        {"signal_id": "arb-queue-ipb", "source_layer": "IPB", "signal_type": "local_self_management"}
    )
    routed = route_agent_signal(signal, observed_at=FIXTURE_CLOCK)
    result = queue.enqueue(
        target_organ="IPB",
        signal_id=signal.signal_id,
        route_class=str(routed.get("route_class", "")),
        route_result=routed,
    )
    assert result["fixture_bridge_only"] is True
    assert result["permission_granted"] is False
    assert queue.depth == 1
    with pytest.raises(ArbValidationError):
        queue.enqueue(
            target_organ="IPB",
            signal_id=signal.signal_id,
            route_class="local_ipb",
            route_result=routed,
            treat_as_authority=True,
        )


def test_bridge_fixture_queues() -> None:
    result = bridge_fixture_queues()
    assert result["fixture_bridge_only"] is True
    assert result["queue_depth"] >= 3


def test_authority_chain_fake_proposal() -> None:
    signal = agent0_signal_from_fixture(
        {
            "signal_id": "arb-proposal-test",
            "source_layer": "SOAR",
            "signal_type": "external_action_request",
            "risk_hint": "high",
        }
    )
    routed = route_agent_signal(signal, observed_at=FIXTURE_CLOCK)
    decision_payload = routed["decision"]
    assert isinstance(decision_payload, dict)
    decision = AgencyRouteDecision(
        route_decision_id=str(decision_payload["route_decision_id"]),
        signal_ref=str(decision_payload["signal_ref"]),
        route_class=decision_payload["route_class"],  # type: ignore[arg-type]
        reason=str(decision_payload["reason"]),
        evidence_refs=tuple(decision_payload["evidence_refs"]),
        required_next_refs=tuple(decision_payload["required_next_refs"]),
        forbidden_next_refs=tuple(decision_payload["forbidden_next_refs"]),
    )
    receipt_payload = routed.get("receipt")
    receipt = None
    if isinstance(receipt_payload, dict):
        receipt = AgencyRoutingReceipt(
            receipt_id=str(receipt_payload["receipt_id"]),
            signal_ref=str(receipt_payload["signal_ref"]),
            route_decision_ref=str(receipt_payload["route_decision_ref"]),
            policy_ref=str(receipt_payload.get("policy_ref", "")),
            conflict_refs=tuple(receipt_payload.get("conflict_refs", ())),
            emitted_events=tuple(receipt_payload.get("emitted_events", ())),
        )
    proposal = dispatch_authority_chain_routing_receipt(signal, decision, receipt)
    assert proposal["fake_dispatch_only"] is True
    assert proposal["proposal"]["permit_minted"] is False  # type: ignore[index]
    assert proposal["proposal"]["oea_ter_called"] is False  # type: ignore[index]
