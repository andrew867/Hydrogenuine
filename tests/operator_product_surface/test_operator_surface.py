"""Operator product surface tests — all P7-A slices."""

from __future__ import annotations

import pytest

from hg_core.exciton_cluster.errors import (
    REFUSED_ACTION_WITHOUT_TARGET_HASH,
    REFUSED_EXCITON_AS_AUTHORITY,
    REFUSED_NATIVE_UI_OFF_BACKBURNER,
    REFUSED_POLISH_IMPLIES_SAFETY,
    REFUSED_SECRET_IN_SURFACE,
    REFUSED_STALE_APPROVAL,
    ExcitonValidationError,
)
from hg_core.exciton_cluster.rtc_design import validate_exciton_rtc_event_design
from hg_runtime.operator_product_surface import (
    FIXTURE_CLOCK,
    ActionDecision,
    OperatorActionRequest,
    OperatorSurfaceDescriptor,
    analyze_fixture_bundles,
    assert_exciton_backburner_boundary,
    audit_surface_polish_claims,
    dispatch_authority_chain_proposal,
    enqueue_fixture_queue,
    load_fixture_bundles,
    load_plt_polish_descriptors,
    planned_exciton_event_refs,
    refuse_action_as_permission,
    refuse_native_ui_off_backburner,
    route_operator_bundle,
)
from hg_runtime.operator_product_surface.classifier import build_polish_assessment, classify_polish_risk
from hg_runtime.operator_product_surface.policies import decide_operator_action, refuse_surface_as_authority
from hg_runtime.operator_product_surface.redaction import contains_secret_material, redact_surface_text
from hg_runtime.operator_product_surface.types import surface_descriptor_from_fixture


def _descriptor(**overrides) -> OperatorSurfaceDescriptor:
    base = dict(
        surface_descriptor_id="ops-surf-test",
        surface="exciton",
        title="Test surface",
        polish_level="mvp",
        safety_disclaimer_visible=True,
        pres_trb_sil_boundaries_stable=True,
        ai_disclosure_visible=True,
        hash_bound_controls_only=True,
        limitation_notice="polish is not safety",
        evidence_refs=("sha256:test",),
        created_at=FIXTURE_CLOCK,
    )
    base.update(overrides)
    return OperatorSurfaceDescriptor(**base)


def _action_request(**overrides) -> OperatorActionRequest:
    base = dict(
        action_request_id="ops-act-test",
        surface="exciton",
        action_kind="observe",
        operator_ref="operator:fixture",
        evidence_refs=("sha256:test",),
        created_at=FIXTURE_CLOCK,
        expires_at="2026-06-15T18:00:00.000000Z",
    )
    base.update(overrides)
    return OperatorActionRequest(**base)


def test_surface_descriptor_schema():
    descriptor = _descriptor()
    assert descriptor.to_payload()["permission_granted"] is False
    assert descriptor.to_payload()["polish_is_not_safety"] is True


def test_surface_descriptor_rejects_authority_created():
    with pytest.raises(ExcitonValidationError):
        _descriptor(authority_created=True)


def test_action_request_rejects_secret_in_scope():
    with pytest.raises(ExcitonValidationError) as exc:
        _action_request(scope_label="api_key=secret")
    assert exc.value.code == REFUSED_SECRET_IN_SURFACE


def test_mutating_action_requires_target_hash():
    with pytest.raises(ExcitonValidationError) as exc:
        _action_request(action_kind="pause_request", target_hash=None)
    assert exc.value.code == REFUSED_ACTION_WITHOUT_TARGET_HASH


def test_action_decision_negative_proofs():
    request = _action_request()
    descriptor = _descriptor()
    assessment = build_polish_assessment(descriptor)
    decision = decide_operator_action(request, assessment)
    ActionDecision.validate_negative_proofs(decision.to_payload())
    assert decision.to_payload()["oea_ter_called"] is False


def test_observe_pulse_advisory_display():
    bundle = next(b for b in load_fixture_bundles() if b["bundle_id"] == "ops-exciton-observe-pulse")
    result = route_operator_bundle(bundle)
    decision = result["route"]["action_decision"]  # type: ignore[index]
    assert decision["decision"] == "advisory_display_only"


def test_hash_bound_pause_recorded():
    bundle = next(b for b in load_fixture_bundles() if b["bundle_id"] == "ops-exciton-hash-bound-pause")
    result = route_operator_bundle(bundle)
    decision = result["route"]["action_decision"]  # type: ignore[index]
    assert decision["decision"] == "hash_bound_request_recorded"


def test_stale_approval_refused():
    bundle = next(b for b in load_fixture_bundles() if b["bundle_id"] == "ops-exciton-stale-approval")
    result = route_operator_bundle(bundle)
    assert result["status"] == "refused"
    decision = result["route"]["action_decision"]  # type: ignore[index]
    assert decision["decision"] == "fail_closed"


def test_polish_implies_safety_contained():
    bundle = next(b for b in load_fixture_bundles() if b["bundle_id"] == "ops-polish-safety-claim")
    result = route_operator_bundle(bundle)
    assert result["status"] == "contained"
    assert result["containment"]["reason_code"] == REFUSED_POLISH_IMPLIES_SAFETY  # type: ignore[index]


def test_approve_requires_authority_chain():
    bundle = next(b for b in load_fixture_bundles() if b["bundle_id"] == "ops-approve-authority-chain")
    result = route_operator_bundle(bundle)
    decision = result["route"]["action_decision"]  # type: ignore[index]
    assert decision["decision"] == "require_authority_chain"


def test_passive_surface_polish_audit():
    audit = audit_surface_polish_claims()
    assert audit["passive_audit_only"] is True
    assert audit["event_count"] >= 9
    assert audit["live_ui_dispatch"] is False


def test_fake_operator_action_queue():
    queue = enqueue_fixture_queue()
    assert queue["fake_queue_only"] is True
    assert queue["queue_depth"] >= 3
    assert queue["live_dispatch"] is False


def test_authority_chain_fake_proposal():
    bundle = next(b for b in load_fixture_bundles() if b["bundle_id"] == "ops-approve-authority-chain")
    result = route_operator_bundle(bundle)
    proposal = result["authority_chain_proposal"]
    assert proposal["fake_dispatch_only"] is True
    assert proposal["proposal"]["permit_minted"] is False  # type: ignore[index]
    assert proposal["proposal"]["oea_ter_called"] is False  # type: ignore[index]


def test_plt_surface_polish_descriptors():
    plt = load_plt_polish_descriptors()
    assert plt["writes_events_only"] is True
    assert plt["surface_count"] >= 5
    assert plt["panic_banner_required_all"] is True


def test_backburner_boundary():
    boundary = assert_exciton_backburner_boundary()
    assert boundary["backburner_guard_active"] is True
    assert boundary["native_ui_deferred"] is True


def test_native_ui_refused_off_backburner():
    with pytest.raises(ExcitonValidationError) as exc:
        refuse_native_ui_off_backburner(allow_native=True)
    assert exc.value.code == REFUSED_NATIVE_UI_OFF_BACKBURNER


def test_surface_not_authority():
    with pytest.raises(ExcitonValidationError) as exc:
        refuse_surface_as_authority(treat_as_authority=True)
    assert exc.value.code == REFUSED_EXCITON_AS_AUTHORITY


def test_action_not_permission():
    with pytest.raises(ExcitonValidationError) as exc:
        refuse_action_as_permission(treat_as_authority=True)
    assert exc.value.code == REFUSED_EXCITON_AS_AUTHORITY


def test_secret_redaction():
    redacted = redact_surface_text("value api_key=abc123 end")
    assert "api_key=" not in redacted
    assert contains_secret_material("api_key=abc")


def test_polish_risk_classifier():
    descriptor = surface_descriptor_from_fixture(
        {
            "surface_descriptor_id": "ops-risk",
            "title": "Friendly green UI means safe panel",
            "safety_disclaimer_visible": "true",
        }
    )
    assert classify_polish_risk(descriptor) == "polish_implies_safety"


def test_fixture_bundles_all_advisory():
    analysis = analyze_fixture_bundles()
    assert analysis["all_advisory"] is True
    assert analysis["bundle_count"] >= 9


def test_planned_rtc_events_valid():
    valid, failures = validate_exciton_rtc_event_design(planned_exciton_event_refs())
    assert valid, failures
    assert len(planned_exciton_event_refs()) >= 14


def test_dispatch_proposal_direct():
    request = _action_request(action_kind="approve_change", target_hash="sha256:target")
    descriptor = _descriptor()
    assessment = build_polish_assessment(descriptor)
    decision = decide_operator_action(request, assessment)
    proposal = dispatch_authority_chain_proposal(request, decision)
    assert proposal["fake_dispatch_only"] is True
    assert proposal["permission_granted"] is False
