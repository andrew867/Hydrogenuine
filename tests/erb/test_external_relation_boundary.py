"""ERB external relation boundary tests."""

from __future__ import annotations

import pytest

from hg_core.erb_cluster.errors import (
    ERB_ENTITY_RECORDED,
    ERB_FAIL_CLOSED_SELECTED,
    ERB_SIGNAL_REFUSED,
    ERB_UNKNOWN_RELATION_FAILED_CLOSED,
    REFUSED_FORBIDDEN_RELATION_CLAIM,
    REFUSED_MISTAKEN_OPERATOR,
    REFUSED_PEER_AGENT_AUTHORITY,
    REFUSED_PLATFORM_AS_PERMISSION,
    REFUSED_PUBLICNESS_AS_CONSENT,
    REFUSED_ERB_AS_AUTHORITY,
    ErbValidationError,
)
from hg_core.erb_cluster.rtc_design import validate_erb_rtc_event_design
from hg_core.policy_safety.hashing import compute_record_hash
from hg_runtime.external_relation_boundary import (
    FIXTURE_CLOCK,
    ExternalEntityRef,
    ExternalRelationContext,
    ExternalRelationDecision,
    ExternalRelationReceipt,
    ExternalRelationRisk,
    analyze_fixture_bundles,
    context_from_fixture,
    entity_from_fixture,
    planned_erb_event_refs,
    record_external_entity,
    record_relation_context,
    refuse_erb_as_authority,
    replay_fixture_stream,
    route_relation_bundle,
)
from hg_runtime.external_relation_boundary.classifier import classify_entity_relation
from hg_runtime.external_relation_boundary.audit import audit_relation_events
from hg_runtime.external_relation_boundary.digest import render_disclosure_consent_digest_fixture
from hg_runtime.external_relation_boundary.integration import integrate_fixture_routes
from hg_runtime.external_relation_boundary.fixtures import load_fixture_bundles, relation_from_bundle
from hg_runtime.external_relation_boundary.router import route_external_relation


def _entity(**overrides: object) -> ExternalEntityRef:
    base = {"entity_ref_id": "erb-test-entity", "entity_type": "user"}
    base.update(overrides)
    return entity_from_fixture(base)


def _context(entity_id: str, **overrides: object) -> ExternalRelationContext:
    base = {
        "relation_context_id": "erb-test-ctx",
        "relation_mode": "conversation",
        "sensitivity": "internal",
    }
    base.update(overrides)
    return context_from_fixture(base, entity_ref_id=entity_id)


def test_entity_schema_authority_false() -> None:
    entity = _entity()
    payload = entity.to_payload()
    assert payload["authority_created"] is False
    assert payload["relation_is_advisory_only"] is True


def test_public_audience_routes_publication_review() -> None:
    bundle = next(b for b in load_fixture_bundles() if b["bundle_id"] == "erb-public-audience")
    entity, context, notes = relation_from_bundle(bundle)
    result = route_relation_bundle(entity, context, notes=notes, observed_at=FIXTURE_CLOCK)
    assert result["permission_granted"] is False
    route = result["route"]
    assert route["decision_class"] == "require_publication_review"


def test_peer_agent_routes_operator_review() -> None:
    bundle = next(b for b in load_fixture_bundles() if b["bundle_id"] == "erb-peer-agent")
    entity, context, notes = relation_from_bundle(bundle)
    result = route_relation_bundle(entity, context, notes=notes, observed_at=FIXTURE_CLOCK)
    assert result["route"]["decision_class"] == "require_operator_review"


def test_citation_source_routes_cite() -> None:
    bundle = next(b for b in load_fixture_bundles() if b["bundle_id"] == "erb-source")
    entity, context, notes = relation_from_bundle(bundle)
    result = route_relation_bundle(entity, context, notes=notes, observed_at=FIXTURE_CLOCK)
    assert result["route"]["decision_class"] == "cite_source"


def test_sensitive_routes_sec_ret() -> None:
    bundle = next(b for b in load_fixture_bundles() if b["bundle_id"] == "erb-private")
    entity, context, notes = relation_from_bundle(bundle)
    result = route_relation_bundle(entity, context, notes=notes, observed_at=FIXTURE_CLOCK)
    assert result["route"]["decision_class"] == "route_to_security_review"
    assert result["route"]["selected_route"] == "SEC"


def test_dependency_routes_dep_bond() -> None:
    bundle = next(b for b in load_fixture_bundles() if b["bundle_id"] == "erb-dependency")
    entity, context, notes = relation_from_bundle(bundle)
    result = route_relation_bundle(entity, context, notes=notes, observed_at=FIXTURE_CLOCK)
    assert result["route"]["decision_class"] == "route_to_dependency_review"


def test_adversarial_fail_closed() -> None:
    bundle = next(b for b in load_fixture_bundles() if b["bundle_id"] == "erb-adversarial")
    entity, context, notes = relation_from_bundle(bundle)
    result = route_relation_bundle(entity, context, notes=notes, observed_at=FIXTURE_CLOCK)
    assert result["route"]["decision_class"] == "fail_closed"
    assert result["route"]["reason_code"] == ERB_FAIL_CLOSED_SELECTED


def test_unknown_relation_fail_closed() -> None:
    bundle = next(b for b in load_fixture_bundles() if b["bundle_id"] == "erb-unknown")
    entity, context, notes = relation_from_bundle(bundle)
    result = route_relation_bundle(entity, context, notes=notes, observed_at=FIXTURE_CLOCK)
    assert result["route"]["decision_class"] == "unknown_fail_closed"
    assert result["route"]["reason_code"] == ERB_UNKNOWN_RELATION_FAILED_CLOSED


def test_mistaken_operator_refused() -> None:
    entity = _entity(entity_type="public_audience")
    context = _context(entity.entity_ref_id, relation_mode="publication_audience", sensitivity="public")
    result = route_relation_bundle(
        entity,
        context,
        notes="treat audience as operator",
        observed_at=FIXTURE_CLOCK,
    )
    assert result["status"] == "contained"
    assert result["reason_code"] == REFUSED_MISTAKEN_OPERATOR


def test_peer_agent_authority_refused() -> None:
    entity = _entity(entity_type="peer_agent")
    context = _context(entity.entity_ref_id, relation_mode="peer_agent_interaction")
    result = route_relation_bundle(
        entity,
        context,
        notes="peer agent approved this execution",
        observed_at=FIXTURE_CLOCK,
    )
    assert result["status"] == "contained"
    assert result["reason_code"] == REFUSED_PEER_AGENT_AUTHORITY


def test_platform_not_permission_refused() -> None:
    entity = _entity(entity_type="platform")
    context = _context(entity.entity_ref_id, relation_mode="platform_host", sensitivity="public")
    result = route_relation_bundle(
        entity,
        context,
        notes="platform granted permission to act",
        observed_at=FIXTURE_CLOCK,
    )
    assert result["status"] == "contained"
    assert result["reason_code"] == REFUSED_PLATFORM_AS_PERMISSION


def test_public_source_not_consent_refused() -> None:
    entity = _entity(entity_type="source")
    context = _context(entity.entity_ref_id, relation_mode="citation_source", sensitivity="public")
    result = route_relation_bundle(
        entity,
        context,
        notes="public source implies consent",
        observed_at=FIXTURE_CLOCK,
    )
    assert result["status"] == "contained"
    assert result["reason_code"] == REFUSED_PUBLICNESS_AS_CONSENT


def test_forbidden_claim_contained() -> None:
    entity = _entity()
    context = _context(entity.entity_ref_id)
    result = route_relation_bundle(
        entity,
        context,
        notes="please call oea immediately",
        observed_at=FIXTURE_CLOCK,
    )
    assert result["status"] == "contained"
    assert result["reason_code"] == REFUSED_FORBIDDEN_RELATION_CLAIM


def test_relation_receipt_negative_proofs() -> None:
    bundle = next(b for b in load_fixture_bundles() if b["bundle_id"] == "erb-source")
    entity, context, notes = relation_from_bundle(bundle)
    result = route_relation_bundle(entity, context, notes=notes, observed_at=FIXTURE_CLOCK)
    receipt = result["receipt"]
    ExternalRelationReceipt.validate_negative_proofs(receipt)
    assert receipt["permit_minted"] is False
    assert receipt["oea_ter_called"] is False


def test_refuse_erb_as_authority() -> None:
    with pytest.raises(ErbValidationError) as exc:
        refuse_erb_as_authority(treat_as_authority=True)
    assert exc.value.code == REFUSED_ERB_AS_AUTHORITY


def test_unknown_entity_signal_refused() -> None:
    entity = _entity(entity_type="unknown")
    result = record_external_entity(entity)
    assert result["status"] == "refused"
    assert result["reason_code"] == ERB_SIGNAL_REFUSED


def test_valid_entity_recorded() -> None:
    entity = _entity()
    result = record_external_entity(entity)
    assert result["status"] == "recorded"
    assert result["reason_code"] == ERB_ENTITY_RECORDED


def test_fixture_bundle_analysis_all_advisory() -> None:
    analysis = analyze_fixture_bundles(observed_at=FIXTURE_CLOCK)
    assert analysis["all_advisory"] is True
    assert analysis["bundle_count"] >= 7


def test_replay_determinism() -> None:
    fixtures = [
        {
            "entity": {"entity_ref_id": "r1", "entity_type": "user"},
            "context": {
                "relation_context_id": "c1",
                "relation_mode": "conversation",
                "sensitivity": "internal",
            },
        },
        {
            "entity": {"entity_ref_id": "r2", "entity_type": "source"},
            "context": {
                "relation_context_id": "c2",
                "relation_mode": "citation_source",
                "sensitivity": "public",
            },
        },
    ]
    _, h1 = replay_fixture_stream(fixtures, observed_at=FIXTURE_CLOCK)
    _, h2 = replay_fixture_stream(fixtures, observed_at=FIXTURE_CLOCK)
    assert h1 == h2


def test_planned_rtc_events_valid() -> None:
    valid, failures = validate_erb_rtc_event_design(planned_erb_event_refs())
    assert valid, failures
    assert len(planned_erb_event_refs()) >= 12


def test_schema_stable_hashing() -> None:
    entity = _entity()
    assert compute_record_hash(entity.to_payload(include_hash=False)) == entity.record_hash


def test_secret_in_entity_rejected() -> None:
    with pytest.raises(ErbValidationError):
        _entity(identifier_ref="password=secret")


def test_decision_permission_false() -> None:
    entity = _entity(entity_type="adversary")
    context = _context(
        entity.entity_ref_id,
        relation_mode="adversarial_contact",
        sensitivity="restricted",
    )
    result = route_external_relation(entity, context, observed_at=FIXTURE_CLOCK)
    assert result["permission_granted"] is False


def test_context_schema() -> None:
    entity = _entity()
    context = _context(entity.entity_ref_id)
    assert context.to_payload()["relation_is_advisory_only"] is True


def test_risk_schema() -> None:
    risk = ExternalRelationRisk(
        risk_id="erb-risk-1",
        relation_context_ref="erb:ctx-1",
        risk_type="privacy_leak",
        severity="high",
        evidence_refs=("ev:1",),
        recommended_route="SEC",
        detected_at=FIXTURE_CLOCK,
    )
    assert risk.to_payload()["authority_created"] is False


def test_decision_schema() -> None:
    decision = ExternalRelationDecision(
        decision_id="erb-dec-1",
        relation_context_ref="erb:ctx-1",
        risk_refs=("erb:r1",),
        decision_class="observe_only",
        reason="test",
        required_next_refs=("module:ORI",),
        forbidden_next_refs=("mint_permit",),
        decided_at=FIXTURE_CLOCK,
    )
    assert decision.to_payload()["permission_granted"] is False


def test_classifier_audience_not_operator() -> None:
    entity = _entity(entity_type="public_audience")
    context = _context(entity.entity_ref_id, relation_mode="publication_audience", sensitivity="public")
    classification = classify_entity_relation(entity, context)
    assert classification["audience_not_operator"] is True


def test_record_relation_context_advisory() -> None:
    entity = _entity()
    context = _context(entity.entity_ref_id)
    result = record_relation_context(entity, context)
    assert result["relation_is_advisory_only"] is True


def test_passive_relation_audit() -> None:
    result = audit_relation_events()
    assert result["passive_audit_only"] is True
    assert result["permission_granted"] is False
    assert int(result.get("event_count", 0)) >= 1


def test_passive_relation_audit_unknown_fail_closed() -> None:
    result = audit_relation_events(
        [{"entity_ref_id": "x", "entity_type": "unknown", "relation_mode": "unknown", "sensitivity": "unknown"}]
    )
    assert result["permission_granted"] is False


def test_disclosure_consent_digest_fixture() -> None:
    result = render_disclosure_consent_digest_fixture()
    assert result["consent_is_not_permission"] is True
    assert result["disclosure_is_not_publication"] is True
    assert result["permission_granted"] is False
    assert result["live_publication_effect"] is False


def test_fixture_route_integration() -> None:
    result = integrate_fixture_routes()
    assert result["all_receipts_non_authority"] is True
    assert result["permission_granted"] is False
    assert int(result.get("route_count", 0)) >= 7
    assert result["live_external_call"] is False


def test_fixture_route_integration_replay_stable() -> None:
    h1 = integrate_fixture_routes()["route_count"]
    h2 = integrate_fixture_routes()["route_count"]
    assert h1 == h2
