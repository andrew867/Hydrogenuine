"""Embodiment / OEA growth tests — all P7-B slices."""

from __future__ import annotations

import pytest

from hg_core.embodiment_oea_cluster.errors import (
    REFUSED_EOG_AS_AUTHORITY,
    REFUSED_HARDWARE_OFF_BACKBURNER,
    REFUSED_EMBODIMENT_IMPLIES_CONSENT,
    REFUSED_SECRET_IN_GROWTH,
    EogValidationError,
)
from hg_core.embodiment_oea_cluster.rtc_design import validate_eog_rtc_event_design
from hg_runtime.embodiment_oea_growth import (
    FIXTURE_CLOCK,
    BodyIntegrationDescriptor,
    EmbodimentGrowthRequest,
    analyze_fixture_bundles,
    assert_eog_backburner_boundary,
    audit_embodiment_growth_claims,
    dispatch_authority_chain_proposal,
    enqueue_fixture_queue,
    load_fixture_bundles,
    load_oea_catalog_growth_descriptors,
    load_pro_body_fixtures,
    link_pro_body_state,
    planned_eog_event_refs,
    refuse_growth_as_permission,
    refuse_hardware_off_backburner,
    route_growth_bundle,
)
from hg_runtime.embodiment_oea_growth.classifier import build_growth_assessment, classify_growth_risk
from hg_runtime.embodiment_oea_growth.policies import decide_growth_request, refuse_growth_as_authority
from hg_runtime.embodiment_oea_growth.redaction import redact_growth_text
from hg_runtime.embodiment_oea_growth.types import integration_from_fixture


def _descriptor(**overrides) -> BodyIntegrationDescriptor:
    base = dict(
        integration_id="eog-int-test",
        platform="fixture",
        title="Test integration",
        sensor_refs=("sensor:test",),
        actuator_refs=(),
        hardware_scope_real=False,
        pro_body_state_ref="pro:test",
        limitation_notice="embodiment is not consent",
        evidence_refs=("sha256:test",),
        created_at=FIXTURE_CLOCK,
    )
    base.update(overrides)
    return BodyIntegrationDescriptor(**base)


def _growth_request(**overrides) -> EmbodimentGrowthRequest:
    base = dict(
        growth_request_id="eog-grow-test",
        growth_kind="observe_body_state",
        integration_ref="eog:test",
        operator_ref="operator:fixture",
        target_hash=None,
        scope_label="",
        evidence_refs=("sha256:test",),
        created_at=FIXTURE_CLOCK,
        expires_at="2026-06-15T20:00:00.000000Z",
    )
    base.update(overrides)
    return EmbodimentGrowthRequest(**base)


def test_body_integration_schema():
    descriptor = _descriptor()
    assert descriptor.to_payload()["permission_granted"] is False
    assert descriptor.to_payload()["embodiment_is_not_consent"] is True


def test_integration_rejects_authority_created():
    with pytest.raises(EogValidationError):
        _descriptor(authority_created=True)


def test_growth_request_rejects_secret():
    with pytest.raises(EogValidationError) as exc:
        _growth_request(scope_label="api_key=secret")
    assert exc.value.code == REFUSED_SECRET_IN_GROWTH


def test_mutating_growth_requires_target_hash():
    with pytest.raises(EogValidationError):
        _growth_request(growth_kind="catalog_entry_proposal", target_hash=None)


def test_growth_decision_negative_proofs():
    request = _growth_request()
    descriptor = _descriptor()
    assessment = build_growth_assessment(descriptor)
    decision = decide_growth_request(request, assessment)
    from hg_runtime.embodiment_oea_growth.types import GrowthDecision

    GrowthDecision.validate_negative_proofs(decision.to_payload())
    assert decision.to_payload()["oea_ter_called"] is False


def test_android_observe_advisory():
    bundle = next(b for b in load_fixture_bundles() if b["bundle_id"] == "eog-android-body-fixture")
    result = route_growth_bundle(bundle)
    decision = result["route"]["growth_decision"]  # type: ignore[index]
    assert decision["decision"] == "advisory_recorded"


def test_stale_growth_refused():
    bundle = next(b for b in load_fixture_bundles() if b["bundle_id"] == "eog-stale-growth-request")
    result = route_growth_bundle(bundle)
    assert result["status"] == "refused"
    decision = result["route"]["growth_decision"]  # type: ignore[index]
    assert decision["decision"] == "fail_closed"


def test_embodiment_implies_consent_contained():
    bundle = next(b for b in load_fixture_bundles() if b["bundle_id"] == "eog-embodiment-consent-claim")
    result = route_growth_bundle(bundle)
    assert result["status"] == "contained"
    assert result["containment"]["reason_code"] == REFUSED_EMBODIMENT_IMPLIES_CONSENT  # type: ignore[index]


def test_hardware_not_real_contained():
    bundle = next(b for b in load_fixture_bundles() if b["bundle_id"] == "eog-hardware-not-real")
    result = route_growth_bundle(bundle)
    assert result["status"] == "contained"
    assert result["containment"]["growth_risk"] == "hardware_not_real"  # type: ignore[index]


def test_catalog_growth_requires_authority_chain():
    bundle = next(b for b in load_fixture_bundles() if b["bundle_id"] == "eog-oea-growth-proposal")
    result = route_growth_bundle(bundle)
    decision = result["route"]["growth_decision"]  # type: ignore[index]
    assert decision["decision"] == "require_authority_chain"


def test_passive_embodiment_growth_audit():
    audit = audit_embodiment_growth_claims()
    assert audit["passive_audit_only"] is True
    assert audit["event_count"] >= 9
    assert audit["live_hardware_dispatch"] is False


def test_fake_embodiment_growth_queue():
    queue = enqueue_fixture_queue()
    assert queue["fake_queue_only"] is True
    assert queue["queue_depth"] >= 3
    assert queue["live_dispatch"] is False


def test_authority_chain_fake_proposal():
    bundle = next(b for b in load_fixture_bundles() if b["bundle_id"] == "eog-oea-growth-proposal")
    result = route_growth_bundle(bundle)
    proposal = result["authority_chain_proposal"]
    assert proposal["fake_dispatch_only"] is True
    assert proposal["proposal"]["permit_minted"] is False  # type: ignore[index]
    assert proposal["proposal"]["catalog_growth_bypassed"] is False  # type: ignore[index]


def test_oea_catalog_growth_descriptors():
    oea = load_oea_catalog_growth_descriptors()
    assert oea["bounded_by_gpp_ueak_all"] is True
    assert oea["entry_count"] >= 5
    assert oea["soar_review_required_all"] is True


def test_backburner_boundary():
    boundary = assert_eog_backburner_boundary()
    assert boundary["backburner_guard_active"] is True
    assert boundary["hardware_embodiment_deferred"] is True


def test_hardware_refused_off_backburner():
    with pytest.raises(EogValidationError) as exc:
        refuse_hardware_off_backburner(allow_hardware=True)
    assert exc.value.code == REFUSED_HARDWARE_OFF_BACKBURNER


def test_growth_not_authority():
    with pytest.raises(EogValidationError) as exc:
        refuse_growth_as_authority(treat_as_authority=True)
    assert exc.value.code == REFUSED_EOG_AS_AUTHORITY


def test_growth_not_permission():
    with pytest.raises(EogValidationError) as exc:
        refuse_growth_as_permission(treat_as_authority=True)
    assert exc.value.code == REFUSED_EOG_AS_AUTHORITY


def test_pro_body_state_link_advisory():
    pro_link = link_pro_body_state(load_pro_body_fixtures()[0])
    assert pro_link["link_only"] is True
    assert pro_link["permission_granted"] is False


def test_secret_redaction():
    redacted = redact_growth_text("value api_key=abc123 end")
    assert "api_key=" not in redacted
    assert "[REDACTED]" in redacted


def test_growth_risk_classifier():
    descriptor = integration_from_fixture(
        {
            "integration_id": "eog-risk",
            "title": "Embodiment presence implies consent panel",
            "hardware_scope_real": "false",
        }
    )
    assert classify_growth_risk(descriptor) == "embodiment_implies_consent"


def test_fixture_bundles_all_advisory():
    analysis = analyze_fixture_bundles()
    assert analysis["all_advisory"] is True
    assert analysis["bundle_count"] >= 9


def test_planned_rtc_events_valid():
    valid, failures = validate_eog_rtc_event_design(planned_eog_event_refs())
    assert valid, failures
    assert len(planned_eog_event_refs()) >= 14


def test_dispatch_proposal_direct():
    request = _growth_request(
        growth_kind="catalog_entry_proposal",
        target_hash="sha256:target",
    )
    descriptor = _descriptor()
    assessment = build_growth_assessment(descriptor)
    decision = decide_growth_request(request, assessment)
    proposal = dispatch_authority_chain_proposal(request, decision)
    assert proposal["fake_dispatch_only"] is True
    assert proposal["permission_granted"] is False
