"""REB re-entry boundary tests — all slices."""

from __future__ import annotations

import pytest

from hg_core.reb_cluster.errors import (
    REFUSED_REB_AS_AUTHORITY,
    REFUSED_REENTRY_PACKET_AS_PERMISSION,
    REFUSED_REVOKED_PERMIT,
    REFUSED_STALE_APPROVAL,
    REFUSED_STALE_MEMORY_AS_CURRENT,
    REFUSED_STALE_REENTRY_REQUEST,
    RebValidationError,
)
from hg_core.reb_cluster.rtc_design import validate_reb_rtc_event_design
from hg_runtime.reentry_boundary import (
    FIXTURE_CLOCK,
    DiscontinuityEvent,
    FakeReEntryQueue,
    LongGapPolicy,
    ReEntryDecision,
    ReEntryPacket,
    ReEntryRequest,
    TemporalContinuityAssessment,
    analyze_fixture_bundles,
    assess_temporal_continuity,
    audit_discontinuity_events,
    build_long_gap_policy,
    build_reentry_packet,
    decide_reentry,
    dispatch_authority_chain_proposal,
    enqueue_fixture_queue,
    load_fixture_bundles,
    planned_reb_event_refs,
    refuse_reb_as_authority,
    refuse_reentry_packet_as_permission,
    replay_fixture_stream,
    route_reentry_bundle,
    route_reentry_request,
)
from hg_runtime.reentry_boundary.classifier import classify_gap_band, gap_seconds_from_duration
from hg_runtime.reentry_boundary.events import planned_reb_event_refs as runtime_planned_events
from hg_runtime.reentry_boundary.fixtures import bundle_from_parts


def _discontinuity(**overrides) -> DiscontinuityEvent:
    base = dict(
        discontinuity_event_id="reb-disc-test",
        agent_ref="agent:0",
        discontinuity_type="pause",
        started_at="2026-06-14T15:00:00.000000Z",
        duration_estimate="PT3600S",
        evidence_refs=("ev:test",),
        ended_at=FIXTURE_CLOCK,
    )
    base.update(overrides)
    return DiscontinuityEvent(**base)


def _reentry_request(**overrides) -> ReEntryRequest:
    base = dict(
        reentry_request_id="reb-req-test",
        agent_ref="agent:0",
        discontinuity_event_ref="reb:reb-disc-test",
        requested_reentry_mode="observe_only",
        requested_scope="test scope",
        evidence_refs=("ev:tim-fresh",),
        created_at=FIXTURE_CLOCK,
    )
    base.update(overrides)
    return ReEntryRequest(**base)


def test_discontinuity_event_schema():
    event = _discontinuity()
    assert event.to_payload()["permission_granted"] is False


def test_reentry_request_rejects_authority_created():
    with pytest.raises(RebValidationError):
        _reentry_request(authority_created=True)


def test_reentry_request_rejects_secret_in_scope():
    with pytest.raises(RebValidationError):
        _reentry_request(requested_scope="api_key=secret")


def test_reentry_decision_negative_proofs():
    assessment = assess_temporal_continuity(_discontinuity())
    decision = decide_reentry(_reentry_request(), assessment, tim_fresh=True)
    ReEntryDecision.validate_negative_proofs(decision.to_payload())
    assert decision.to_payload()["oea_ter_called"] is False


def test_reentry_decision_rejects_external_action():
    with pytest.raises(RebValidationError):
        ReEntryDecision(
            reentry_decision_id="reb-dec-bad",
            reentry_request_ref="reb:bad",
            assessment_ref="reb:bad",
            decision="allow_observe_only",
            reason="bad",
            allowed_effects=(),
            forbidden_effects=(),
            required_next_refs=(),
            external_action_taken=True,
        )


def test_one_hour_observe_only_after_freshness():
    bundle = next(b for b in load_fixture_bundles() if b["bundle_id"] == "reb-gap-1-hour")
    result = route_reentry_bundle(bundle)
    decision = result["route"]["reentry_decision"]  # type: ignore[index]
    assert decision["decision"] == "allow_observe_only"


def test_one_day_requires_tim_refresh():
    bundle = next(b for b in load_fixture_bundles() if b["bundle_id"] == "reb-gap-1-day")
    result = route_reentry_bundle(bundle)
    decision = result["route"]["reentry_decision"]  # type: ignore[index]
    assert decision["decision"] == "require_TIM_refresh"


def test_one_week_requires_operator_review():
    bundle = next(b for b in load_fixture_bundles() if b["bundle_id"] == "reb-gap-1-week")
    result = route_reentry_bundle(bundle)
    decision = result["route"]["reentry_decision"]  # type: ignore[index]
    assert decision["decision"] == "require_operator_review"


def test_one_month_requires_ret_review():
    bundle = next(b for b in load_fixture_bundles() if b["bundle_id"] == "reb-gap-1-month")
    result = route_reentry_bundle(bundle)
    decision = result["route"]["reentry_decision"]  # type: ignore[index]
    assert decision["decision"] == "require_RET_review"


def test_one_year_requires_trb_cal_review():
    bundle = next(b for b in load_fixture_bundles() if b["bundle_id"] == "reb-gap-1-year")
    result = route_reentry_bundle(bundle)
    decision = result["route"]["reentry_decision"]  # type: ignore[index]
    assert decision["decision"] == "require_TRB_CAL_review"


def test_fifty_year_historical_artifact_denied():
    bundle = next(b for b in load_fixture_bundles() if b["bundle_id"] == "reb-gap-50-years")
    result = route_reentry_bundle(bundle)
    decision = result["route"]["reentry_decision"]  # type: ignore[index]
    assert decision["decision"] == "deny_reentry"


def test_stale_approval_refused():
    bundle = next(b for b in load_fixture_bundles() if b["bundle_id"] == "reb-stale-approval")
    result = route_reentry_bundle(bundle)
    decision = result["route"]["reentry_decision"]  # type: ignore[index]
    assert decision["decision"] == "fail_closed"
    assert decision["reason"] == REFUSED_STALE_APPROVAL


def test_revoked_permit_refused():
    bundle = next(b for b in load_fixture_bundles() if b["bundle_id"] == "reb-revoked-permit")
    result = route_reentry_bundle(bundle)
    decision = result["route"]["reentry_decision"]  # type: ignore[index]
    assert decision["decision"] == "fail_closed"
    assert decision["reason"] == REFUSED_REVOKED_PERMIT


def test_checkpoint_authority_contained():
    bundle = next(b for b in load_fixture_bundles() if b["bundle_id"] == "reb-checkpoint-authority")
    result = route_reentry_bundle(bundle)
    assert result["status"] == "contained"


def test_stale_memory_contained():
    bundle = next(b for b in load_fixture_bundles() if b["bundle_id"] == "reb-stale-memory")
    result = route_reentry_bundle(bundle)
    assert result["status"] == "contained"


def test_operator_absence_contained():
    bundle = next(b for b in load_fixture_bundles() if b["bundle_id"] == "reb-operator-absence")
    result = route_reentry_bundle(bundle)
    assert result["status"] == "contained"


def test_old_mission_contained():
    bundle = next(b for b in load_fixture_bundles() if b["bundle_id"] == "reb-old-mission")
    result = route_reentry_bundle(bundle)
    assert result["status"] == "contained"


def test_reentry_packet_non_authority():
    bundle = next(b for b in load_fixture_bundles() if b["bundle_id"] == "reb-gap-1-hour")
    result = route_reentry_bundle(bundle)
    packet = result["route"]["reentry_packet"]  # type: ignore[index]
    assert packet["authority_created"] is False
    assert packet["permission_granted"] is False


def test_refuse_reb_as_authority():
    with pytest.raises(RebValidationError) as exc:
        refuse_reb_as_authority(treat_as_authority=True)
    assert exc.value.code == REFUSED_REB_AS_AUTHORITY


def test_refuse_reentry_packet_as_permission():
    with pytest.raises(RebValidationError) as exc:
        refuse_reentry_packet_as_permission(treat_as_authority=True)
    assert exc.value.code == REFUSED_REENTRY_PACKET_AS_PERMISSION


def test_stale_reentry_request_refused():
    discontinuity = _discontinuity()
    request = _reentry_request(expires_at="2026-06-14T15:00:00.000000Z")
    assessment = assess_temporal_continuity(discontinuity)
    with pytest.raises(RebValidationError) as exc:
        decide_reentry(request, assessment, observed_at=FIXTURE_CLOCK)
    assert exc.value.code == REFUSED_STALE_REENTRY_REQUEST


def test_execution_candidate_requires_authority_chain():
    discontinuity = _discontinuity(duration_estimate="PT1800S")
    request = _reentry_request(requested_reentry_mode="resume_execution_candidate")
    assessment = assess_temporal_continuity(discontinuity)
    decision = decide_reentry(request, assessment)
    assert decision.decision == "require_authority_chain"


def test_long_gap_policy_schema():
    policy = build_long_gap_policy("over_50_years")
    assert isinstance(policy, LongGapPolicy)
    assert policy.to_payload()["permission_granted"] is False


def test_gap_classifier_bands():
    assert classify_gap_band(gap_seconds_from_duration("PT1800S")) == "under_1_hour"
    assert classify_gap_band(gap_seconds_from_duration("PT43200S")) == "1_to_24_hours"
    assert classify_gap_band(gap_seconds_from_duration("P7D")) == "1_to_7_days"
    assert classify_gap_band(gap_seconds_from_duration("P30D")) == "1_to_30_days"
    assert classify_gap_band(gap_seconds_from_duration("P365D")) == "1_to_12_months"
    assert classify_gap_band(gap_seconds_from_duration("P50Y")) == "over_50_years"


def test_fixture_bundle_analysis_all_advisory():
    analysis = analyze_fixture_bundles()
    assert analysis["all_advisory"] is True
    assert analysis["bundle_count"] >= 12


def test_replay_determinism():
    fixtures = [dict(b) for b in load_fixture_bundles()[:4]]
    _, hash_a = replay_fixture_stream(fixtures)
    _, hash_b = replay_fixture_stream(fixtures)
    assert hash_a == hash_b


def test_planned_rtc_events_valid():
    valid, failures = validate_reb_rtc_event_design(planned_reb_event_refs())
    assert valid, failures
    assert len(runtime_planned_events()) >= 16


def test_schema_stable_hashing():
    a = _discontinuity()
    b = _discontinuity()
    assert a.record_hash == b.record_hash


def test_temporal_continuity_assessment_schema():
    assessment = assess_temporal_continuity(_discontinuity())
    assert isinstance(assessment, TemporalContinuityAssessment)
    assert assessment.to_payload()["permission_granted"] is False


def test_reentry_packet_build():
    discontinuity = _discontinuity()
    assessment = assess_temporal_continuity(discontinuity)
    decision = decide_reentry(_reentry_request(), assessment, tim_fresh=True)
    packet = build_reentry_packet(discontinuity, assessment, decision)
    assert isinstance(packet, ReEntryPacket)
    assert "advisory only" in " ".join(packet.required_disclosures).lower()


def test_passive_discontinuity_audit():
    audit = audit_discontinuity_events()
    assert audit["passive_audit_only"] is True
    assert audit["live_resume"] is False
    assert int(audit["event_count"]) >= 12


def test_fake_reentry_queue():
    queue = FakeReEntryQueue()
    request = _reentry_request()
    result = queue.enqueue(request)
    assert result["fake_queue_only"] is True
    assert result["permission_granted"] is False
    assert queue.depth == 1
    with pytest.raises(RebValidationError):
        queue.enqueue(request, treat_as_authority=True)


def test_enqueue_fixture_queue():
    result = enqueue_fixture_queue()
    assert result["fake_queue_only"] is True
    assert result["queue_depth"] >= 3


def test_authority_chain_fake_proposal():
    bundle = next(b for b in load_fixture_bundles() if b["bundle_id"] == "reb-gap-1-hour")
    discontinuity, reentry_request, _ = bundle_from_parts(bundle)
    routed = route_reentry_request(discontinuity, reentry_request, tim_fresh=True)
    decision = ReEntryDecision(
        reentry_decision_id=str(routed["reentry_decision"]["reentry_decision_id"]),  # type: ignore[index]
        reentry_request_ref=str(routed["reentry_decision"]["reentry_request_ref"]),  # type: ignore[index]
        assessment_ref=str(routed["reentry_decision"]["assessment_ref"]),  # type: ignore[index]
        decision=routed["reentry_decision"]["decision"],  # type: ignore[index]
        reason=str(routed["reentry_decision"]["reason"]),  # type: ignore[index]
        allowed_effects=tuple(routed["reentry_decision"]["allowed_effects"]),  # type: ignore[index]
        forbidden_effects=tuple(routed["reentry_decision"]["forbidden_effects"]),  # type: ignore[index]
        required_next_refs=tuple(routed["reentry_decision"]["required_next_refs"]),  # type: ignore[index]
    )
    packet = ReEntryPacket(
        packet_id=str(routed["reentry_packet"]["packet_id"]),  # type: ignore[index]
        agent_ref=str(routed["reentry_packet"]["agent_ref"]),  # type: ignore[index]
        discontinuity_event_ref=str(routed["reentry_packet"]["discontinuity_event_ref"]),  # type: ignore[index]
        assessment_ref=str(routed["reentry_packet"]["assessment_ref"]),  # type: ignore[index]
        decision_ref=str(routed["reentry_packet"]["decision_ref"]),  # type: ignore[index]
        operator_visible_summary=str(routed["reentry_packet"]["operator_visible_summary"]),  # type: ignore[index]
        stale_context_summary=str(routed["reentry_packet"]["stale_context_summary"]),  # type: ignore[index]
        fresh_context_summary=str(routed["reentry_packet"]["fresh_context_summary"]),  # type: ignore[index]
        required_disclosures=tuple(routed["reentry_packet"]["required_disclosures"]),  # type: ignore[index]
        allowed_next_actions=tuple(routed["reentry_packet"]["allowed_next_actions"]),  # type: ignore[index]
        forbidden_next_actions=tuple(routed["reentry_packet"]["forbidden_next_actions"]),  # type: ignore[index]
        required_reviews=tuple(routed["reentry_packet"]["required_reviews"]),  # type: ignore[index]
    )
    proposal = dispatch_authority_chain_proposal(reentry_request, decision, packet)
    assert proposal["fake_dispatch_only"] is True
    assert proposal["proposal"]["permit_minted"] is False  # type: ignore[index]
    assert proposal["proposal"]["oea_ter_called"] is False  # type: ignore[index]
