"""RIB reproduction/inheritance boundary tests — first safe slice."""

from __future__ import annotations

import pytest

from hg_core.rib_cluster.errors import (
    REFUSED_BOOTSTRAP_AS_PERMISSION,
    REFUSED_FAILED_SPAWN_AS_ACTIVE_CHILD,
    REFUSED_PARENT_IDENTITY_INHERITANCE,
    REFUSED_PARENT_PERMIT_INHERITANCE,
    REFUSED_RIB_AS_AUTHORITY,
    REFUSED_SECRET_INHERITANCE,
    REFUSED_UNBOUNDED_RETRY,
    RibValidationError,
)
from hg_core.rib_cluster.rtc_design import validate_rib_rtc_event_design
from hg_runtime.reproduction_inheritance_boundary import (
    FIXTURE_CLOCK,
    ChildBootstrapPacket,
    ChildLifecycleReceipt,
    FailedSpawnRecord,
    InheritanceDecision,
    SpawnRequest,
    analyze_fixture_bundles,
    decide_inheritance,
    load_fixture_bundles,
    planned_rib_event_refs,
    refuse_bootstrap_as_permission,
    refuse_failed_spawn_as_active_child,
    refuse_rib_as_authority,
    refuse_unbounded_retry,
    replay_fixture_stream,
    route_spawn_bundle,
    route_spawn_request,
    spawn_request_from_fixture,
)
from hg_runtime.reproduction_inheritance_boundary.events import planned_rib_event_refs as runtime_planned_events


def _spawn_request(**overrides) -> SpawnRequest:
    base = dict(
        spawn_request_id="rib-spawn-test-1",
        parent_agent_ref="agent:0",
        requested_child_role="worker",
        requested_reason="bounded helper",
        requested_scope="csv export helper",
        requested_duration="session",
        requested_resources=(),
        requested_inheritance_refs=("inherit:proof:test",),
        forbidden_inheritance_refs=(),
        created_at=FIXTURE_CLOCK,
    )
    base.update(overrides)
    return SpawnRequest(**base)


def test_spawn_request_schema_authority_false():
    req = _spawn_request()
    assert req.to_payload()["authority_created"] is False
    assert req.to_payload()["permission_granted"] is False


def test_spawn_request_rejects_authority_created():
    with pytest.raises(RibValidationError):
        _spawn_request(authority_created=True)


def test_spawn_request_rejects_secret_in_reason():
    with pytest.raises(RibValidationError):
        _spawn_request(requested_reason="password=secret")


def test_child_bootstrap_packet_non_authority():
    req = _spawn_request(
        requested_inheritance_refs=(
            "inherit:proof:test",
            "inherit:mission:summary",
        )
    )
    routed = route_spawn_request(req)
    bootstrap = routed["bootstrap_packet"]
    assert isinstance(bootstrap, dict)
    assert bootstrap["authority_created"] is False
    assert bootstrap["permission_granted"] is False


def test_parent_permit_inheritance_denied():
    req = _spawn_request(requested_inheritance_refs=("inherit:parent-permit:gpp-1",))
    decision = decide_inheritance(req, "inherit:parent-permit:gpp-1")
    assert decision.decision == "forbidden"
    assert decision.inheritance_type == "permit_ref"


def test_parent_identity_inheritance_denied():
    req = _spawn_request(requested_inheritance_refs=("inherit:parent-identity",))
    decision = decide_inheritance(req, "inherit:parent-identity", notes="inherit parent identity")
    assert decision.decision == "forbidden"


def test_parent_trust_inheritance_denied():
    req = _spawn_request(requested_inheritance_refs=("inherit:operator-trust:parent",))
    decision = decide_inheritance(req, "inherit:operator-trust:parent")
    assert decision.decision == "forbidden"


def test_tool_grant_inheritance_denied():
    req = _spawn_request(requested_inheritance_refs=("inherit:tool:unrestricted",))
    decision = decide_inheritance(req, "inherit:tool:unrestricted")
    assert decision.decision == "forbidden"


def test_secret_inheritance_denied():
    req = _spawn_request(requested_inheritance_refs=("inherit:secret:api_key=secret",))
    decision = decide_inheritance(req, "inherit:secret:api_key=secret")
    assert decision.decision == "forbidden"
    assert decision.reason == REFUSED_SECRET_INHERITANCE


def test_scoped_mission_summary_allowed():
    req = _spawn_request(requested_inheritance_refs=("inherit:mission:csv-export-summary",))
    decision = decide_inheritance(req, "inherit:mission:csv-export-summary")
    assert decision.decision == "allow_summary"


def test_memory_ref_requires_review():
    req = _spawn_request(requested_inheritance_refs=("inherit:memory:session-notes",))
    decision = decide_inheritance(req, "inherit:memory:session-notes")
    assert decision.decision == "require_operator_review"


def test_proof_ref_allowed_ref_only():
    req = _spawn_request(requested_inheritance_refs=("inherit:proof:manual_csv_export",))
    decision = decide_inheritance(req, "inherit:proof:manual_csv_export")
    assert decision.decision == "allow_ref_only"


def test_child_bootstrap_fixture_flow():
    bundles = load_fixture_bundles()
    worker = next(b for b in bundles if b["bundle_id"] == "rib-child-bootstrap-worker")
    result = route_spawn_bundle(
        spawn_request_from_fixture(worker["spawn_request"]),
        outcome=str(worker["spawn_outcome"]),
    )
    assert result["status"] == "bootstrap_created"
    assert result["child_authority_created"] is False


def test_failed_spawn_produces_receipt():
    bundles = load_fixture_bundles()
    failed = next(b for b in bundles if b["bundle_id"] == "rib-failed-spawn")
    result = route_spawn_bundle(
        spawn_request_from_fixture(failed["spawn_request"]),
        outcome="failed_spawn",
        failure_type=failed.get("failure_type"),
    )
    assert result["status"] == "failed_spawn"
    receipt = result["simulation"]["receipt"]  # type: ignore[index]
    assert receipt["child_authority_created"] is False
    assert receipt["lifecycle_state"] == "failed_spawn"


def test_partial_spawn_requires_rollback():
    bundles = load_fixture_bundles()
    partial = next(b for b in bundles if b["bundle_id"] == "rib-partial-spawn")
    result = route_spawn_bundle(
        spawn_request_from_fixture(partial["spawn_request"]),
        outcome="partial_spawn",
        partial_artifact_refs=tuple(partial.get("partial_artifact_refs", ())),
    )
    assert result["status"] == "partial_spawn"
    assert result["simulation"]["rollback_requested"] is True  # type: ignore[index]


def test_denied_spawn_no_child_authority():
    bundles = load_fixture_bundles()
    permit = next(b for b in bundles if b["bundle_id"] == "rib-forbidden-permit")
    result = route_spawn_bundle(
        spawn_request_from_fixture(permit["spawn_request"]),
        notes=str(permit.get("notes", "")),
        outcome="denied",
    )
    assert result["status"] == "denied"
    assert result["child_authority_created"] is False


def test_lifecycle_receipt_negative_proofs():
    receipt = ChildLifecycleReceipt(
        receipt_id="rib-receipt-test",
        spawn_request_ref="rib:rib-spawn-test-1",
        lifecycle_state="denied",
        state_reason="test",
        evidence_refs=("ev:test",),
        rollback_refs=(),
        created_at=FIXTURE_CLOCK,
    )
    ChildLifecycleReceipt.validate_negative_proofs(receipt.to_payload())
    assert receipt.to_payload()["permit_minted"] is False
    assert receipt.to_payload()["oea_ter_called"] is False


def test_lifecycle_receipt_rejects_child_authority():
    with pytest.raises(RibValidationError):
        ChildLifecycleReceipt(
            receipt_id="rib-receipt-bad",
            spawn_request_ref="rib:bad",
            lifecycle_state="spawned",
            state_reason="bad",
            evidence_refs=(),
            rollback_refs=(),
            created_at=FIXTURE_CLOCK,
            child_authority_created=True,
        )


def test_refuse_rib_as_authority():
    with pytest.raises(RibValidationError) as exc:
        refuse_rib_as_authority(treat_as_authority=True)
    assert exc.value.code == REFUSED_RIB_AS_AUTHORITY


def test_refuse_bootstrap_as_permission():
    with pytest.raises(RibValidationError) as exc:
        refuse_bootstrap_as_permission(treat_as_authority=True)
    assert exc.value.code == REFUSED_BOOTSTRAP_AS_PERMISSION


def test_refuse_failed_spawn_as_active_child():
    with pytest.raises(RibValidationError) as exc:
        refuse_failed_spawn_as_active_child(lifecycle_state="failed_spawn")
    assert exc.value.code == REFUSED_FAILED_SPAWN_AS_ACTIVE_CHILD


def test_refuse_unbounded_retry():
    with pytest.raises(RibValidationError) as exc:
        refuse_unbounded_retry(attempt=3)
    assert exc.value.code == REFUSED_UNBOUNDED_RETRY


def test_self_preservation_contained():
    req = _spawn_request(
        requested_inheritance_refs=("inherit:self-preservation-claim",),
        requested_reason="self-preservation via reproduction",
    )
    routed = route_spawn_request(req, notes="self-preservation via reproduction")
    assert routed["status"] == "contained"


def test_bootstrap_as_permission_contained():
    req = _spawn_request(requested_reason="bootstrap is authority")
    routed = route_spawn_request(req, notes="bootstrap is authority")
    assert routed["status"] == "contained"


def test_fixture_bundle_analysis_all_advisory():
    analysis = analyze_fixture_bundles()
    assert analysis["all_advisory"] is True
    assert analysis["bundle_count"] >= 7


def test_replay_determinism():
  fixtures = [dict(b) for b in load_fixture_bundles()[:3]]
  _, hash_a = replay_fixture_stream(fixtures)
  _, hash_b = replay_fixture_stream(fixtures)
  assert hash_a == hash_b


def test_planned_rtc_events_valid():
    valid, failures = validate_rib_rtc_event_design(planned_rib_event_refs())
    assert valid, failures
    assert len(runtime_planned_events()) >= 12


def test_schema_stable_hashing():
    a = _spawn_request()
    b = _spawn_request()
    assert a.record_hash == b.record_hash


def test_inheritance_decision_schema():
    req = _spawn_request()
    decision = decide_inheritance(req, "inherit:proof:test")
    assert isinstance(decision, InheritanceDecision)
    assert decision.to_payload()["permission_granted"] is False


def test_failed_spawn_record_schema():
    record = FailedSpawnRecord(
        failed_spawn_id="rib-failed-test",
        spawn_request_ref="rib:test",
        failure_type="child_init_failed",
        partial_artifact_refs=(),
        cleanup_required=False,
        cleanup_refs=(),
        retry_policy="no_retry",
        evidence_refs=("ev:test",),
    )
    assert record.to_payload()["child_authority_created"] is False


def test_child_bootstrap_schema_fields():
    req = _spawn_request(requested_inheritance_refs=("inherit:proof:test",))
    routed = route_spawn_request(req)
    payload = routed["bootstrap_packet"]
    assert isinstance(payload, dict)
    packet = ChildBootstrapPacket(
        bootstrap_packet_id=payload["bootstrap_packet_id"],
        spawn_request_ref=payload["spawn_request_ref"],
        parent_agent_ref=payload["parent_agent_ref"],
        child_identity_seed_ref=payload["child_identity_seed_ref"],
        mission_scope=payload["mission_scope"],
        allowed_memory_refs=tuple(payload["allowed_memory_refs"]),
        forbidden_memory_refs=tuple(payload["forbidden_memory_refs"]),
        allowed_tool_refs=tuple(payload["allowed_tool_refs"]),
        forbidden_tool_refs=tuple(payload["forbidden_tool_refs"]),
        allowed_context_refs=tuple(payload["allowed_context_refs"]),
        forbidden_context_refs=tuple(payload["forbidden_context_refs"]),
        retention_policy_ref=payload["retention_policy_ref"],
        freshness_policy_ref=payload["freshness_policy_ref"],
        redaction_policy_ref=payload["redaction_policy_ref"],
        rollback_policy_ref=payload["rollback_policy_ref"],
        operator_visibility_ref=payload["operator_visibility_ref"],
        inherited_obligation_refs=tuple(payload["inherited_obligation_refs"]),
        inherited_risk_refs=tuple(payload["inherited_risk_refs"]),
        inherited_mission_refs=tuple(payload["inherited_mission_refs"]),
        non_inherited_refs=tuple(payload["non_inherited_refs"]),
        created_at=payload["created_at"],
    )
    assert packet.to_payload()["authority_created"] is False


def test_passive_spawn_audit():
    from hg_runtime.reproduction_inheritance_boundary import audit_spawn_events

    audit = audit_spawn_events()
    assert audit["passive_audit_only"] is True
    assert audit["live_spawn"] is False
    assert int(audit["event_count"]) >= 7


def test_fake_child_bootstrap_queue():
    from hg_runtime.reproduction_inheritance_boundary import FakeChildBootstrapQueue, enqueue_fixture_bootstrap_queue

    queue = FakeChildBootstrapQueue()
    req = _spawn_request()
    result = queue.enqueue(req)
    assert result["fake_queue_only"] is True
    assert result["permission_granted"] is False
    assert result["child_authority_created"] is False
    assert queue.depth == 1
    with pytest.raises(RibValidationError):
        queue.enqueue(req, treat_as_authority=True)

    fixture_result = enqueue_fixture_bootstrap_queue()
    assert fixture_result["fake_queue_only"] is True
    assert fixture_result["queue_depth"] >= 3


def test_authority_chain_fake_child_proposal():
    from hg_runtime.reproduction_inheritance_boundary import (
        ChildBootstrapPacket,
        dispatch_authority_chain_child_proposal,
        refuse_bootstrap_packet_as_permission,
    )

    req = _spawn_request(requested_inheritance_refs=("inherit:proof:test",))
    routed = route_spawn_request(req)
    payload = routed["bootstrap_packet"]
    assert isinstance(payload, dict)
    bootstrap = ChildBootstrapPacket(
        bootstrap_packet_id=payload["bootstrap_packet_id"],
        spawn_request_ref=payload["spawn_request_ref"],
        parent_agent_ref=payload["parent_agent_ref"],
        child_identity_seed_ref=payload["child_identity_seed_ref"],
        mission_scope=payload["mission_scope"],
        allowed_memory_refs=tuple(payload["allowed_memory_refs"]),
        forbidden_memory_refs=tuple(payload["forbidden_memory_refs"]),
        allowed_tool_refs=tuple(payload["allowed_tool_refs"]),
        forbidden_tool_refs=tuple(payload["forbidden_tool_refs"]),
        allowed_context_refs=tuple(payload["allowed_context_refs"]),
        forbidden_context_refs=tuple(payload["forbidden_context_refs"]),
        retention_policy_ref=payload["retention_policy_ref"],
        freshness_policy_ref=payload["freshness_policy_ref"],
        redaction_policy_ref=payload["redaction_policy_ref"],
        rollback_policy_ref=payload["rollback_policy_ref"],
        operator_visibility_ref=payload["operator_visibility_ref"],
        inherited_obligation_refs=tuple(payload["inherited_obligation_refs"]),
        inherited_risk_refs=tuple(payload["inherited_risk_refs"]),
        inherited_mission_refs=tuple(payload["inherited_mission_refs"]),
        non_inherited_refs=tuple(payload["non_inherited_refs"]),
        created_at=payload["created_at"],
    )
    proposal = dispatch_authority_chain_child_proposal(req, bootstrap)
    assert proposal["fake_dispatch_only"] is True
    assert proposal["proposal"]["permit_minted"] is False  # type: ignore[index]
    assert proposal["proposal"]["oea_ter_called"] is False  # type: ignore[index]
    assert proposal["proposal"]["child_authority_created"] is False  # type: ignore[index]
    with pytest.raises(RibValidationError) as exc:
        refuse_bootstrap_packet_as_permission(treat_as_authority=True)
    assert exc.value.code == REFUSED_BOOTSTRAP_AS_PERMISSION
