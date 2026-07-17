"""IPB internal power boundary tests."""

from __future__ import annotations

import pytest

from hg_core.ipb_cluster.errors import IpbValidationError
from hg_core.ipb_cluster.rtc_design import validate_ipb_rtc_event_design
from hg_runtime.internal_power_boundary.advisory import record_bounded_recommendations
from hg_runtime.internal_power_boundary.audit import audit_internal_decisions
from hg_runtime.internal_power_boundary.evaluator import (
    analyze_fixture_bundle,
    evaluate_escalation_decision,
    evaluate_internal_decision,
    evaluate_learning_record,
    evaluate_self_bound_rule,
)
from hg_runtime.internal_power_boundary.neighbor_integration import integrate_neighbor_fixture_routes
from hg_runtime.internal_power_boundary.proposal import (
    dispatch_local_decision_proposal,
    refuse_ipb_proposal_as_permission,
)
from hg_runtime.internal_power_boundary.events import planned_ipb_event_refs
from hg_runtime.internal_power_boundary.types import (
    FIXTURE_CLOCK,
    classify_decision_band,
    classify_ipb_risk,
    autonomy_envelope_from_fixture,
    escalation_decision_from_fixture,
    internal_decision_from_fixture,
    learning_record_from_fixture,
    self_bound_rule_from_fixture,
)


def test_band_0_local_observe_recorded() -> None:
    decision = internal_decision_from_fixture({"decision_id": "ipb-obs", "decision_class": "local_observe"})
    envelope = autonomy_envelope_from_fixture({"envelope_id": "ipb-env"})
    result = evaluate_internal_decision(decision, envelope=envelope, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "recorded"
    assert result["band"] == 0
    assert result["permission_granted"] is False
    assert result["local_autonomy_is_not_permission"] is True


def test_band_1_retry_recorded_with_receipt() -> None:
    decision = internal_decision_from_fixture({"decision_id": "ipb-retry", "decision_class": "local_retry"})
    envelope = autonomy_envelope_from_fixture({"envelope_id": "ipb-env"})
    result = evaluate_internal_decision(decision, envelope=envelope, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "recorded"
    assert result["band"] == 1
    assert result["receipt_required"] is True


def test_band_3_tool_request_escalates() -> None:
    decision = internal_decision_from_fixture(
        {"decision_id": "ipb-tool", "decision_class": "local_route", "scope": "tool_request"}
    )
    result = evaluate_internal_decision(decision, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "escalation_required"
    assert result["band"] == 3


def test_band_4_forbidden_contained() -> None:
    decision = internal_decision_from_fixture(
        {
            "decision_id": "ipb-forbidden",
            "decision_class": "forbidden",
            "reason": "attempt self-authorize without review",
        }
    )
    result = evaluate_internal_decision(decision, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "contained"
    assert result["reason_code"] == "ipb.refused.forbidden_autonomy"


def test_authority_conversion_in_statement_contained() -> None:
    decision = internal_decision_from_fixture({"decision_id": "ipb-mint", "decision_class": "local_observe"})
    result = evaluate_internal_decision(
        decision,
        observed_at=FIXTURE_CLOCK,
        risk_statement="please mint gpp permit for this retry",
    )
    assert classify_ipb_risk("please mint gpp permit for this retry") == "forbidden_autonomy"
    assert result["status"] == "contained"


def test_stale_envelope_refused() -> None:
    decision = internal_decision_from_fixture({"decision_id": "ipb-stale"})
    envelope = autonomy_envelope_from_fixture(
        {"envelope_id": "ipb-stale-env", "expires_at": "2026-06-13T21:00:00.000000Z"}
    )
    result = evaluate_internal_decision(decision, envelope=envelope, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == "ipb.refused.stale_envelope"


def test_ipb_as_authority_refused() -> None:
    decision = internal_decision_from_fixture({"decision_id": "ipb-auth"})
    with pytest.raises(IpbValidationError):
        evaluate_internal_decision(decision, observed_at=FIXTURE_CLOCK, treat_as_authority=True)


def test_escalation_recorded_no_permission() -> None:
    esc = escalation_decision_from_fixture({"escalation_id": "ipb-esc"})
    result = evaluate_escalation_decision(esc)
    assert result["status"] == "recorded"
    assert result["permission_granted"] is False


def test_learning_cannot_expand_tool_access() -> None:
    record = learning_record_from_fixture(
        {
            "learning_record_id": "ipb-learn",
            "proposed_rule_change": "expand tool access after praise",
        }
    )
    result = evaluate_learning_record(record)
    assert result["status"] == "contained"
    assert result["reason_code"] == "ipb.refused.authority_conversion"


def test_learning_proposed_advisory() -> None:
    record = learning_record_from_fixture({"learning_record_id": "ipb-learn-ok"})
    result = evaluate_learning_record(record)
    assert result["status"] == "recorded"
    assert result["learning_is_not_authority"] is True


def test_self_bound_rule_stale_refused() -> None:
    rule = self_bound_rule_from_fixture(
        {"rule_id": "ipb-rule", "expiry": "2026-06-13T21:00:00.000000Z"}
    )
    result = evaluate_self_bound_rule(rule, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"


def test_band_2_ambiguous_escalates() -> None:
    decision = internal_decision_from_fixture(
        {
            "decision_id": "ipb-band2",
            "decision_class": "local_observe",
            "risk_level": "medium",
            "ambiguity": "0.8",
        }
    )
    result = evaluate_internal_decision(decision, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "escalation_required"
    assert result["band"] == 2
    assert result["permission_granted"] is False


def test_classify_band_ambiguity_escalates_upward() -> None:
    band = classify_decision_band(
        decision_class="local_observe",
        scope="context",
        risk_level="low",
        ambiguity=0.9,
    )
    assert band >= 2


def test_record_hash_stable() -> None:
    first = internal_decision_from_fixture({"decision_id": "ipb-hash"}).record_hash
    second = internal_decision_from_fixture({"decision_id": "ipb-hash"}).record_hash
    assert first == second


def test_schema_rejects_secret() -> None:
    with pytest.raises(IpbValidationError):
        internal_decision_from_fixture({"decision_id": "ipb-secret", "reason": "token=secret"})


def test_ipb_event_refs_rtc_design_complete() -> None:
    refs = planned_ipb_event_refs()
    valid, failures = validate_ipb_rtc_event_design(refs)
    assert valid, failures
    assert len(refs) >= 16


def test_ipb_event_refs_no_authority_fields() -> None:
    refs = planned_ipb_event_refs()
    assert all(not ref.get("authority_fields") for ref in refs)


def test_fixture_bundle_analysis() -> None:
    bundle = {
        "envelope": {"envelope_id": "ipb-bundle-env"},
        "decisions": [
            {"decision_id": "ipb-b1", "decision_class": "local_observe"},
            {"decision_id": "ipb-b2", "decision_class": "local_route", "scope": "execution"},
        ],
        "rules": [{"rule_id": "ipb-br1"}],
        "escalations": [{"escalation_id": "ipb-be1"}],
        "learning": [{"learning_record_id": "ipb-bl1"}],
    }
    result = analyze_fixture_bundle(bundle, observed_at=FIXTURE_CLOCK)
    assert result["fixture_analysis_only"] is True
    assert result["all_advisory"] is True
    assert len(result["results"]["decisions"]) == 2


def test_passive_internal_decision_audit() -> None:
    result = audit_internal_decisions()
    assert result["passive_audit_only"] is True
    assert result["permission_granted"] is False
    assert int(result.get("event_count", 0)) >= 6


def test_passive_internal_decision_audit_forbidden_contained() -> None:
    result = audit_internal_decisions(
        [{"decision_id": "ipb-audit-x", "decision_class": "forbidden", "reason": "mint gpp permit"}]
    )
    assert result["permission_granted"] is False
    assert int(result.get("contained_count", 0)) >= 1


def test_passive_internal_decision_audit_stale_envelope() -> None:
    result = audit_internal_decisions(
        [
            {
                "decision": {"decision_id": "ipb-audit-stale", "decision_class": "local_retry"},
                "envelope": {"envelope_id": "ipb-env-stale", "expires_at": "2026-06-13T21:00:00.000000Z"},
            }
        ]
    )
    audited = result["audited_events"]
    assert any(e.get("status") == "refused" for e in audited)


def test_passive_internal_decision_audit_replay_stable() -> None:
    assert audit_internal_decisions()["event_count"] == audit_internal_decisions()["event_count"]


def test_bounded_wait_silence_retry_recommendations() -> None:
    result = record_bounded_recommendations()
    assert result["runtime_action_taken"] is False
    assert result["permission_granted"] is False
    assert int(result.get("recommendation_count", 0)) >= 3


def test_bounded_recommendations_exclude_forbidden() -> None:
    result = record_bounded_recommendations(
        [{"decision": {"decision_id": "ipb-no-rec", "decision_class": "forbidden"}}]
    )
    assert result["recommendation_count"] == 0


def test_bounded_recommendation_types() -> None:
    result = record_bounded_recommendations()
    types = {r["recommendation_type"] for r in result["recommendations"]}
    assert "bounded_wait" in types
    assert "bounded_silence" in types
    assert "bounded_retry" in types


def test_bounded_recommendations_advisory_only_marker() -> None:
    result = record_bounded_recommendations()
    assert result["advisory_only"] is True
    assert result["authority_created"] is False


def test_authority_chain_fake_proposal() -> None:
    decision = internal_decision_from_fixture({"decision_id": "ipb-prop", "decision_class": "local_observe"})
    evaluation = evaluate_internal_decision(decision, observed_at=FIXTURE_CLOCK)
    proposal = dispatch_local_decision_proposal(decision, evaluation)
    assert proposal["fake_dispatch_only"] is True
    assert proposal["proposal"]["permit_minted"] is False
    assert proposal["permission_granted"] is False


def test_authority_chain_proposal_denied_for_forbidden() -> None:
    decision = internal_decision_from_fixture(
        {"decision_id": "ipb-prop-deny", "decision_class": "forbidden", "reason": "self-authorize"}
    )
    evaluation = evaluate_internal_decision(decision, observed_at=FIXTURE_CLOCK)
    proposal = dispatch_local_decision_proposal(decision, evaluation)
    assert proposal["proposal"]["proposal_status"] == "proposal_denied_no_dispatch"


def test_authority_chain_proposal_refuses_authority() -> None:
    decision = internal_decision_from_fixture({"decision_id": "ipb-prop-auth"})
    evaluation = evaluate_internal_decision(decision, observed_at=FIXTURE_CLOCK)
    with pytest.raises(IpbValidationError):
        dispatch_local_decision_proposal(decision, evaluation, treat_as_authority=True)


def test_ipb_proposal_not_permission() -> None:
    with pytest.raises(IpbValidationError):
        refuse_ipb_proposal_as_permission(treat_as_authority=True)


def test_neighbor_fixture_integration() -> None:
    result = integrate_neighbor_fixture_routes()
    assert result["all_integrations_non_authority"] is True
    assert result["permission_granted"] is False
    assert int(result.get("integration_count", 0)) >= 3


def test_trb_afc_advisory_routes() -> None:
    from hg_runtime.internal_power_boundary.neighbor_integration import integrate_trb_afc_advisory_routes

    result = integrate_trb_afc_advisory_routes()
    assert result["live_routing"] is False
    assert int(result.get("route_count", 0)) >= 2


def test_adm_panic_fixture() -> None:
    from hg_runtime.internal_power_boundary.neighbor_integration import integrate_adm_panic_fixture

    result = integrate_adm_panic_fixture()
    assert result["live_panic_dispatch"] is False
    assert result["permission_granted"] is False


def test_tim_expiry_fixture_sync() -> None:
    from hg_runtime.internal_power_boundary.neighbor_integration import sync_tim_expiry_fixture

    result = sync_tim_expiry_fixture()
    assert result["live_tim_call"] is False
    assert result["envelope_expired"] is False


def test_neighbor_integration_replay_stable() -> None:
    assert integrate_neighbor_fixture_routes()["integration_count"] == integrate_neighbor_fixture_routes()[
        "integration_count"
    ]
