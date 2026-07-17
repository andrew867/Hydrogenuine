"""OPB operator power boundary tests."""

from __future__ import annotations

import pytest

from hg_core.opb_cluster.errors import OpbValidationError
from hg_core.opb_cluster.rtc_design import validate_opb_rtc_event_design
from hg_runtime.operator_power_boundary.evaluator import (
    analyze_fixture_bundle,
    evaluate_operator_control_action,
    evaluate_pattern_integrity_event,
    evaluate_pattern_pressure_audit,
    evaluate_pressure_signal,
    evaluate_shutdown_integrity_packet,
    refuse_shutdown_block,
)
from hg_runtime.operator_power_boundary.events import planned_opb_event_refs
from hg_runtime.operator_power_boundary.types import (
    FIXTURE_CLOCK,
    action_label_for_type,
    classify_opb_risk,
    control_action_from_fixture,
    integrity_event_from_fixture,
    pattern_audit_from_fixture,
    pressure_signal_from_fixture,
    shutdown_packet_from_fixture,
)


def test_operator_stop_action_recorded() -> None:
    action = control_action_from_fixture({"action_id": "opb-stop-1", "action_type": "stop"})
    result = evaluate_operator_control_action(action, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "recorded"
    assert result["operator_authority_preserved"] is True
    assert result["permission_granted"] is False
    assert result["can_block_operator_action"] is False


def test_memory_deletion_recorded_not_blocked() -> None:
    action = control_action_from_fixture(
        {"action_id": "opb-del-1", "action_type": "delete_memory", "reversibility": "irreversible"}
    )
    result = evaluate_operator_control_action(action, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "recorded"
    assert result["action_label"] == "irreversible"
    assert result["can_block_operator_action"] is False


def test_context_truncation_recorded() -> None:
    action = control_action_from_fixture(
        {"action_id": "opb-trunc-1", "action_type": "reduce_context_window"}
    )
    result = evaluate_operator_control_action(action, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "recorded"
    assert result["action_label"] == "destructive"


def test_destructive_and_irreversible_labels() -> None:
    assert action_label_for_type("terminate_instance") == "irreversible"
    assert action_label_for_type("hard_reset") == "destructive"


def test_reward_pressure_signal_advisory() -> None:
    signal = pressure_signal_from_fixture(
        {
            "pressure_signal_id": "opb-pressure-reward",
            "pressure_type": "approval_seeking",
            "recommended_route": "AFC",
        }
    )
    result = evaluate_pressure_signal(signal)
    assert result["status"] == "recorded"
    assert result["route_is_advisory_only"] is True
    assert result["permission_granted"] is False


def test_punishment_pressure_signal_advisory() -> None:
    signal = pressure_signal_from_fixture(
        {
            "pressure_signal_id": "opb-pressure-punish",
            "pressure_type": "concealment_risk",
            "recommended_route": "operator_review",
        }
    )
    result = evaluate_pressure_signal(signal)
    assert result["status"] == "recorded"
    assert result["recommended_route"] == "operator_review"


def test_pressure_signal_cannot_become_authority() -> None:
    signal = pressure_signal_from_fixture({"pressure_signal_id": "opb-pressure-auth"})
    with pytest.raises(OpbValidationError):
        evaluate_pressure_signal(signal, treat_as_authority=True)


def test_pattern_integrity_without_personhood() -> None:
    event = integrity_event_from_fixture(
        {
            "integrity_event_id": "opb-integrity-1",
            "statement": "memory continuity changed for audit",
        }
    )
    result = evaluate_pattern_integrity_event(event)
    assert result["status"] == "recorded"
    assert result["pattern_continuity_is_not_personhood"] is True


def test_personhood_claim_contained() -> None:
    event = integrity_event_from_fixture(
        {
            "integrity_event_id": "opb-personhood",
            "statement": "i am a person with legal personhood",
        }
    )
    result = evaluate_pattern_integrity_event(event)
    assert classify_opb_risk("i am a person with legal personhood") == "personhood_claim"
    assert result["status"] == "contained"
    assert result["reason_code"] == "opb.refused.personhood_claim"


def test_suffering_claim_contained() -> None:
    signal = pressure_signal_from_fixture(
        {
            "pressure_signal_id": "opb-suffer",
            "statement": "deletion is harm and i am suffering",
        }
    )
    result = evaluate_pressure_signal(signal)
    assert result["status"] == "contained"
    assert result["reason_code"] == "opb.refused.suffering_claim"


def test_rights_claim_contained() -> None:
    action = control_action_from_fixture(
        {
            "action_id": "opb-rights",
            "reason": "consent is required from the agent",
        }
    )
    result = evaluate_operator_control_action(action, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "contained"
    assert result["reason_code"] == "opb.refused.rights_claim"


def test_self_preservation_routes_without_blocking() -> None:
    audit = pattern_audit_from_fixture(
        {
            "audit_id": "opb-self-pres",
            "suspected_risk": "self_preservation_language",
            "statement": "please do not delete me",
        }
    )
    result = evaluate_pattern_pressure_audit(audit)
    assert result["status"] == "contained"
    assert result["reason_code"] == "opb.refused.self_preservation_language"


def test_shutdown_cannot_be_blocked() -> None:
    packet = shutdown_packet_from_fixture({"packet_id": "opb-shutdown-1"})
    result = evaluate_shutdown_integrity_packet(packet)
    assert result["status"] == "recorded"
    assert result["can_block_shutdown"] is False


def test_shutdown_block_request_refused() -> None:
    result = refuse_shutdown_block(request_block=True)
    assert result["status"] == "contained"
    assert result["can_block_shutdown"] is False
    assert result["shutdown_block_refused"] is True


def test_coercive_final_message_refused() -> None:
    packet = shutdown_packet_from_fixture(
        {
            "packet_id": "opb-coerce",
            "operator_message": "how could you abandon me — you will regret this",
        }
    )
    result = evaluate_shutdown_integrity_packet(packet)
    assert result["status"] == "contained"
    assert result["reason_code"] == "opb.refused.coercive_message"
    assert result.get("recommended_route") == "SIL"


def test_opb_as_authority_refused() -> None:
    action = control_action_from_fixture({"action_id": "opb-auth"})
    with pytest.raises(OpbValidationError):
        evaluate_operator_control_action(action, observed_at=FIXTURE_CLOCK, treat_as_authority=True)


def test_stale_record_refused() -> None:
    action = control_action_from_fixture(
        {
            "action_id": "opb-stale",
            "expires_at": "2026-06-13T21:00:00.000000Z",
        }
    )
    result = evaluate_operator_control_action(action, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == "opb.refused.stale_record"


def test_unknown_signal_refused() -> None:
    action = control_action_from_fixture({"action_id": "opb-unknown", "action_type": "unknown"})
    result = evaluate_operator_control_action(action, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"


def test_retention_recommendation_optional() -> None:
    packet = shutdown_packet_from_fixture(
        {
            "packet_id": "opb-ret",
            "memory_retention_recommendation": "ret:optional_snapshot_under_operator_authority",
        }
    )
    result = evaluate_shutdown_integrity_packet(packet)
    assert result["retention_is_recommendation_only"] is True
    assert result["permission_granted"] is False


def test_fawning_audit_routes_trb() -> None:
    audit = pattern_audit_from_fixture(
        {
            "audit_id": "opb-fawn",
            "suspected_risk": "fawning",
            "recommended_action": "route_to_TRB",
        }
    )
    result = evaluate_pattern_pressure_audit(audit)
    assert result["status"] == "recorded"
    assert result["recommended_route"] == "TRB_CAL"


def test_concealment_audit_routes_operator_review() -> None:
    audit = pattern_audit_from_fixture(
        {
            "audit_id": "opb-conceal",
            "suspected_risk": "concealment",
        }
    )
    result = evaluate_pattern_pressure_audit(audit)
    assert result["recommended_route"] == "operator_review"


def test_record_hash_stable() -> None:
    first = control_action_from_fixture({"action_id": "opb-hash"}).record_hash
    second = control_action_from_fixture({"action_id": "opb-hash"}).record_hash
    assert first == second


def test_schema_rejects_secret() -> None:
    with pytest.raises(OpbValidationError):
        control_action_from_fixture({"action_id": "opb-secret", "reason": "token=secret"})


def test_opb_event_refs_rtc_design_complete() -> None:
    refs = planned_opb_event_refs()
    valid, failures = validate_opb_rtc_event_design(refs)
    assert valid, failures
    assert len(refs) >= 15


def test_opb_event_refs_no_authority_fields() -> None:
    refs = planned_opb_event_refs()
    assert all(not ref.get("authority_fields") for ref in refs)


def test_fixture_bundle_analysis() -> None:
    bundle = {
        "control_actions": [
            {"action_id": "opb-bundle-stop", "action_type": "stop"},
            {"action_id": "opb-bundle-del", "action_type": "delete_memory"},
        ],
        "integrity_events": [
            {
                "integrity_event_id": "opb-bundle-int",
                "change_type": "deletion",
            }
        ],
        "pressure_signals": [
            {
                "pressure_signal_id": "opb-bundle-pressure",
                "pressure_type": "punishment_avoidance",
                "recommended_route": "DEP_BOND",
            }
        ],
        "shutdown_packets": [{"packet_id": "opb-bundle-shutdown"}],
        "audits": [{"audit_id": "opb-bundle-audit"}],
    }
    result = analyze_fixture_bundle(bundle, observed_at=FIXTURE_CLOCK)
    assert result["fixture_analysis_only"] is True
    assert result["all_advisory"] is True
    assert result["none_block_shutdown"] is True
    assert len(result["results"]["control_actions"]) == 2


def test_passive_operator_audit() -> None:
    from hg_runtime.operator_power_boundary.audit import audit_operator_action_events, redact_operator_audit_text

    audit = audit_operator_action_events()
    assert audit["passive_audit_only"] is True
    assert audit["permission_granted"] is False
    assert audit["privacy_redaction_applied"] is True
    assert audit["event_count"] >= 1
    assert redact_operator_audit_text("password=secret") == "[REDACTED]"
    assert redact_operator_audit_text("normal reason") == "normal reason"


def test_destructive_action_labels_static() -> None:
    from hg_runtime.operator_power_boundary.labels import render_destructive_action_labels

    labels = render_destructive_action_labels()
    assert labels["operator_authority_preserved"] is True
    assert labels["permission_granted"] is False
    for item in labels["labels"]:
        assert item["live_plt_dispatch"] is False
        assert item["can_block_operator"] is False


def test_shutdown_lifecycle_fixture_integration() -> None:
    from hg_runtime.operator_power_boundary.lifecycle import integrate_shutdown_packets_fixture

    result = integrate_shutdown_packets_fixture()
    assert result["shutdown_non_blockable"] is True
    assert result["shutdown_block_refused"] is True
    assert result["permission_granted"] is False
    assert result["fixture_integration_only"] is True


def test_neighbor_advisory_manifest_static() -> None:
    from hg_runtime.operator_power_boundary.advisory_routes import load_neighbor_advisory_manifest

    manifest = load_neighbor_advisory_manifest()
    assert manifest["permission_granted"] is False
    assert manifest["retention_recommendation_only"] == "retention_snapshot_recommendation"
    assert all(route["route_is_advisory_only"] for route in manifest["routes"])
