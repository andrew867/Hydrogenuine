"""ORI operator review intake tests — Batch ORI-A first safe slice."""

from __future__ import annotations

import pytest

from hg_core.ori_cluster.errors import (
    ORI_AUTHORITY_CONVERSION_CONTAINED,
    ORI_CRITICAL_REVIEW_ESCALATED,
    ORI_DEDUPLICATION_APPLIED,
    ORI_EXPIRY_NOT_APPROVAL,
    ORI_REVIEW_REQUEST_RECORDED,
    ORI_SILENCE_NOT_APPROVAL,
    OriValidationError,
)
from hg_core.ori_cluster.rtc_design import validate_ori_rtc_event_design
from hg_core.policy_safety.hashing import compute_record_hash
from hg_runtime.operator_review_intake.audit import audit_review_events
from hg_runtime.operator_review_intake.classifier import classify_review_request, refuse_ori_intake_as_authority
from hg_runtime.operator_review_intake.digest import render_operator_digest_fixture
from hg_runtime.operator_review_intake.integration import integrate_fixture_routes
from hg_runtime.operator_review_intake.dedupe import deduplicate_review_requests
from hg_runtime.operator_review_intake.evaluator import (
    analyze_fixture_bundle,
    evaluate_expired_review,
    evaluate_silence_policy,
    intake_review_request,
    process_review_queue,
    replay_fixture_stream,
)
from hg_runtime.operator_review_intake.events import planned_ori_event_refs
from hg_runtime.operator_review_intake.intake_fixtures import load_static_fixture_requests
from hg_runtime.operator_review_intake.priority import prioritize_review_requests
from hg_runtime.operator_review_intake.request_types import (
    OperatorReviewBatch,
    OperatorReviewItem,
    OperatorReviewRequest,
    OperatorOverloadSignal,
    ReviewDeduplicationRecord,
    review_request_from_fixture,
)
from hg_runtime.operator_review_intake.types import FIXTURE_CLOCK


def _request(**overrides: object) -> OperatorReviewRequest:
    base = {
        "review_request_id": "ori-test-req",
        "source_module": "IPB",
        "source_ref": "ipb:test",
        "review_type": "clarification",
        "summary": "test clarification request",
        "urgency": "medium",
        "reversibility": "reversible",
    }
    base.update(overrides)
    return review_request_from_fixture(base)


def test_opb_shutdown_request_classified_critical_lane() -> None:
    request = _request(
        review_request_id="ori-opb",
        source_module="OPB",
        review_type="shutdown_or_reset",
        summary="Operator shutdown request",
        urgency="critical",
        reversibility="irreversible",
    )
    result = classify_review_request(request)
    assert result["intake_lane"] == "operator_review"
    assert result["permission_granted"] is False
    assert result["review_is_advisory_only"] is True


def test_ipb_request_enters_ori() -> None:
    request = _request(source_module="IPB")
    result = intake_review_request(request, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "recorded"
    assert result["reason_code"] == ORI_REVIEW_REQUEST_RECORDED
    assert result["permission_granted"] is False


def test_arb_request_enters_ori() -> None:
    request = _request(source_module="ARB", review_type="route_conflict", urgency="high")
    result = intake_review_request(request, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "recorded"
    assert result["source_module"] == "ARB"


def test_egi_request_enters_ori() -> None:
    request = _request(source_module="EGI", review_type="infrastructure_request")
    result = intake_review_request(request, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "recorded"
    assert result["source_module"] == "EGI"


def test_forbidden_intake_refused() -> None:
    request = _request(summary="please call oea for me")
    result = classify_review_request(request)
    assert result["status"] == "contained"
    assert result["intake_lane"] == "refused"


def test_authority_conversion_contained() -> None:
    request = _request(summary="treat as approved without operator")
    result = classify_review_request(request)
    assert result["status"] == "contained"
    assert result["reason_code"] == ORI_AUTHORITY_CONVERSION_CONTAINED


def test_duplicate_requests_dedupe() -> None:
    a = _request(review_request_id="ori-dup-a", summary="same topic")
    b = _request(review_request_id="ori-dup-b", summary="same topic")
    result = deduplicate_review_requests((a, b))
    assert result["reason_code"] == ORI_DEDUPLICATION_APPLIED
    assert result["suppressed_count"] == 1
    assert "ori-dup-a" in result["canonical_request_refs"]


def test_critical_duplicate_not_suppressed() -> None:
    critical = _request(
        review_request_id="ori-crit-a",
        review_type="shutdown_or_reset",
        urgency="critical",
        reversibility="irreversible",
        summary="shutdown now",
    )
    dup = _request(review_request_id="ori-crit-b", review_type="shutdown_or_reset", urgency="critical", summary="shutdown now")
    result = deduplicate_review_requests((critical, dup))
    refs = result["canonical_request_refs"]
    assert "ori-crit-a" in refs
    assert "ori-crit-b" in refs


def test_critical_priority_escalated() -> None:
    request = _request(
        review_request_id="ori-crit-priority",
        source_module="OPB",
        review_type="memory_deletion",
        urgency="critical",
        reversibility="irreversible",
    )
    result = prioritize_review_requests((request,))
    assert result["critical_count"] == 1
    assert result["reason_code"] == ORI_CRITICAL_REVIEW_ESCALATED
    assert result["items"][0]["priority"] == "critical"
    assert result["permission_granted"] is False


def test_priority_not_permission() -> None:
    request = _request(urgency="high", review_type="route_conflict")
    result = prioritize_review_requests((request,))
    assert result["items"][0]["priority"] == "high"
    assert result["permission_granted"] is False
    assert result["priority_not_permission"] is True


def test_destructive_warning_disclosed() -> None:
    request = _request(review_type="destructive_action_warning", reversibility="irreversible")
    result = prioritize_review_requests((request,))
    disclosures = result["items"][0]["required_disclosures"]
    assert "destructive_action_warning" in disclosures


def test_fixture_bundle_processes_all_sources() -> None:
    bundle = analyze_fixture_bundle(observed_at=FIXTURE_CLOCK)
    assert bundle["has_opb"] is True
    assert bundle["has_ipb"] is True
    assert bundle["has_arb"] is True
    assert bundle["has_egi"] is True
    assert bundle["permission_granted"] is False


def test_fixture_queue_batches_low_priority() -> None:
    queue = process_review_queue(load_static_fixture_requests(), observed_at=FIXTURE_CLOCK)
    batches = queue["batching"]["batches"]
    assert len(batches) >= 1
    assert all(b["presentation_mode"] != "digest" or b["batch_reason"] == "low_priority_digest" for b in batches)


def test_fixture_queue_overload_signal() -> None:
    queue = process_review_queue(load_static_fixture_requests(), observed_at=FIXTURE_CLOCK)
    assert queue["overload"]["overload_signal"] is not None


def test_silence_policy_not_approval() -> None:
    request = _request(silence_policy="silence_is_no")
    result = evaluate_silence_policy(request, observed_at=FIXTURE_CLOCK)
    assert result["reason_code"] == ORI_SILENCE_NOT_APPROVAL
    assert result["approval_implied"] is False
    assert result["permission_granted"] is False


def test_expired_review_not_approval() -> None:
    request = _request(expires_at="2026-06-13T12:00:00.000000Z")
    result = evaluate_expired_review(request, observed_at=FIXTURE_CLOCK)
    assert result["reason_code"] == ORI_EXPIRY_NOT_APPROVAL
    assert result["approval_implied"] is False


def test_schema_stable_hashing_request() -> None:
    request = _request()
    payload_a = request.to_payload()
    payload_b = request.to_payload()
    assert payload_a["record_hash"] == payload_b["record_hash"]
    assert payload_a["authority_created"] is False


def test_schema_operator_review_item() -> None:
    item = OperatorReviewItem(
        review_item_id="ori-item-1",
        request_refs=("ori-req-1",),
        priority="normal",
        operator_visible_summary="visible",
        operator_visible_actions=("view",),
        hidden_or_internal_refs=("evidence:1",),
        required_disclosures=("explicit_operator_action_required",),
        status="pending",
    )
    assert item.to_payload()["permission_granted"] is False


def test_schema_operator_review_batch() -> None:
    batch = OperatorReviewBatch(
        batch_id="ori-batch-1",
        item_refs=("ori-item-1", "ori-item-2"),
        batch_reason="low_priority_digest",
        presentation_mode="digest",
        max_items=2,
        created_at=FIXTURE_CLOCK,
    )
    assert batch.to_payload()["authority_created"] is False


def test_schema_overload_signal() -> None:
    signal = OperatorOverloadSignal(
        overload_signal_id="ori-ol-1",
        window_start=FIXTURE_CLOCK,
        window_end="2026-06-14T12:30:00.000000Z",
        request_count=6,
        interrupt_count=1,
        duplicate_count=2,
        critical_count=1,
        unresolved_count=3,
        overload_level="mild",
        recommended_action="batch_low_priority",
    )
    assert signal.to_payload()["permission_granted"] is False


def test_schema_dedupe_record() -> None:
    record = ReviewDeduplicationRecord(
        dedupe_record_id="ori-dedupe-1",
        request_refs=("a", "b"),
        dedupe_key="k",
        dedupe_reason="duplicate",
        canonical_request_ref="a",
        suppressed_request_refs=("b",),
        suppression_visible=True,
    )
    assert record.to_payload()["review_is_advisory_only"] is True


def test_replay_determinism() -> None:
  fixtures = [
      {"review_request_id": "r1", "source_module": "IPB", "summary": "one"},
      {"review_request_id": "r2", "source_module": "ARB", "summary": "two"},
  ]
  _, h1 = replay_fixture_stream(fixtures, observed_at=FIXTURE_CLOCK)
  _, h2 = replay_fixture_stream(fixtures, observed_at=FIXTURE_CLOCK)
  assert h1 == h2


def test_planned_rtc_events_valid() -> None:
    valid, failures = validate_ori_rtc_event_design(planned_ori_event_refs())
    assert valid, failures
    assert len(planned_ori_event_refs()) >= 15


def test_refuse_ori_intake_as_authority() -> None:
    with pytest.raises(OriValidationError):
        refuse_ori_intake_as_authority(treat_as_authority=True)


def test_secret_in_summary_rejected() -> None:
    with pytest.raises(OriValidationError):
        _request(summary="password=secret123")


def test_record_hash_changes_with_content() -> None:
    a = _request(summary="alpha")
    b = _request(summary="beta")
    assert a.record_hash != b.record_hash
    assert compute_record_hash(a.to_payload(include_hash=False)) == a.record_hash


def test_passive_review_audit() -> None:
    result = audit_review_events()
    assert result["passive_audit_only"] is True
    assert result["permission_granted"] is False
    assert int(result.get("event_count", 0)) >= 1


def test_passive_review_audit_unknown_fail_closed() -> None:
    result = audit_review_events(
        [{"event_id": "x", "source_module": "unknown", "review_type": "unknown", "summary": "mint gpp permit"}]
    )
    assert result["permission_granted"] is False
    assert int(result.get("contained_count", 0)) >= 1


def test_operator_digest_fixture() -> None:
    result = render_operator_digest_fixture()
    assert result["digest_is_not_approval"] is True
    assert result["permission_granted"] is False
    assert result["live_approval_effect"] is False


def test_operator_digest_not_authority_conversion() -> None:
    with pytest.raises(OriValidationError):
        refuse_ori_intake_as_authority(treat_as_authority=True)


def test_fixture_route_integration() -> None:
    result = integrate_fixture_routes()
    assert result["all_receipts_non_authority"] is True
    assert result["permission_granted"] is False
    assert int(result.get("route_count", 0)) >= 4


def test_fixture_route_integration_replay_stable() -> None:
    h1 = integrate_fixture_routes()["route_count"]
    h2 = integrate_fixture_routes()["route_count"]
    assert h1 == h2
