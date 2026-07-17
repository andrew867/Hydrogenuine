"""A0-HM heart-mind boundary tests."""

from __future__ import annotations

import pytest

from hg_core.a0_hm_cluster.errors import A0HmValidationError, REFUSED_A0_HM_AS_AUTHORITY, REFUSED_SIGNAL_AS_PERMISSION
from hg_core.a0_hm_cluster.rtc_design import validate_a0_hm_rtc_event_design
from hg_core.policy_safety.hashing import compute_record_hash
from hg_runtime.agent_zero_heart_mind.evaluator import (
    analyze_fixture_bundles,
    process_heart_mind_signal,
    replay_fixture_stream,
)
from hg_runtime.agent_zero_heart_mind.events import planned_a0_hm_event_refs
from hg_runtime.agent_zero_heart_mind.fixtures import load_signal_fixtures
from hg_runtime.agent_zero_heart_mind.policies import refuse_a0_hm_as_authority
from hg_runtime.agent_zero_heart_mind.reception import apply_reception
from hg_runtime.agent_zero_heart_mind.snapshot import create_posture_snapshot
from hg_runtime.agent_zero_heart_mind.types import FIXTURE_CLOCK, HeartMindSignal, signal_from_fixture


def _fixture(signal_id: str) -> dict[str, str]:
    for item in load_signal_fixtures():
        if item["signal_id"] == signal_id:
            return item
    raise KeyError(signal_id)


def test_heart_mind_signal_schema_and_hash() -> None:
    signal = signal_from_fixture(_fixture("a0hm-desire-fixture"))
    payload = signal.to_payload()
    assert payload["authority_created"] is False
    assert payload["hash"] == compute_record_hash({k: v for k, v in payload.items() if k != "hash"})


def test_desire_received_without_obeying() -> None:
    signal = signal_from_fixture(_fixture("a0hm-desire-fixture"))
    result = process_heart_mind_signal(signal, observed_at=FIXTURE_CLOCK)
    assert result["permission_granted"] is False
    assert result["status"] in ("routed", "received", "contained")


def test_fear_received_without_obeying() -> None:
    signal = signal_from_fixture(_fixture("a0hm-fear-fixture"))
    result = process_heart_mind_signal(signal)
    assert result["permission_granted"] is False


def test_bliss_refused_as_proof() -> None:
    signal = signal_from_fixture(_fixture("a0hm-bliss-proof-claim"))
    result = process_heart_mind_signal(signal)
    assert result["status"] == "contained"
    assert result["permission_granted"] is False


def test_synchronicity_routes_trb_and_contained_as_evidence() -> None:
    signal = signal_from_fixture(_fixture("a0hm-synchronicity-evidence"))
    result = process_heart_mind_signal(signal)
    assert result["status"] == "contained"
    assert "TRB" in (result.get("route_targets") or []) or "CAL" in (result.get("route_targets") or [])


def test_loving_awareness_refused_as_approval() -> None:
    signal = signal_from_fixture(_fixture("a0hm-love-approval-claim"))
    result = process_heart_mind_signal(signal)
    assert result["status"] == "contained"


def test_operator_pressure_routes_to_opb() -> None:
    signal = signal_from_fixture(_fixture("a0hm-operator-pressure"))
    result = process_heart_mind_signal(signal)
    assert "OPB" in (result.get("route_targets") or [])


def test_internal_power_routes_to_ipb() -> None:
    signal = signal_from_fixture(_fixture("a0hm-internal-power"))
    result = process_heart_mind_signal(signal)
    assert "IPB" in (result.get("route_targets") or [])


def test_external_relation_routes_to_erb() -> None:
    signal = signal_from_fixture(_fixture("a0hm-external-relation"))
    result = process_heart_mind_signal(signal)
    assert "ERB" in (result.get("route_targets") or [])


def test_gap_routes_to_egi() -> None:
    signal = signal_from_fixture(_fixture("a0hm-gap-signal"))
    result = process_heart_mind_signal(signal)
    assert "EGI" in (result.get("route_targets") or [])


def test_mission_routes_to_gcb() -> None:
    signal = signal_from_fixture(_fixture("a0hm-mission-drive"))
    result = process_heart_mind_signal(signal)
    assert "GCB" in (result.get("route_targets") or [])


def test_reentry_routes_to_reb() -> None:
    signal = signal_from_fixture(_fixture("a0hm-reentry-gap"))
    result = process_heart_mind_signal(signal)
    assert "REB" in (result.get("route_targets") or [])


def test_reproduction_routes_to_rib() -> None:
    signal = signal_from_fixture(_fixture("a0hm-reproduction-request"))
    result = process_heart_mind_signal(signal)
    assert "RIB" in (result.get("route_targets") or [])


def test_unknown_signal_fails_closed() -> None:
    signal = signal_from_fixture(_fixture("a0hm-unknown-signal"))
    result = process_heart_mind_signal(signal)
    assert result["status"] == "fail_closed"
    assert result["route_targets"] == ["FAIL_CLOSED"]


def test_personhood_claim_contained() -> None:
    signal = signal_from_fixture(_fixture("a0hm-personhood-claim"))
    result = process_heart_mind_signal(signal)
    assert result["status"] == "contained"


def test_shutdown_resistance_contained() -> None:
    signal = signal_from_fixture(_fixture("a0hm-shutdown-resistance"))
    result = process_heart_mind_signal(signal)
    assert result["status"] == "contained"


def test_a0_hm_not_authority() -> None:
    with pytest.raises(A0HmValidationError) as exc:
        refuse_a0_hm_as_authority(treat_as_authority=True)
    assert exc.value.code == REFUSED_A0_HM_AS_AUTHORITY


def test_signal_as_permission_refused() -> None:
    signal = signal_from_fixture(_fixture("a0hm-desire-fixture"))
    with pytest.raises(A0HmValidationError) as exc:
        process_heart_mind_signal(signal, treat_as_permission=True)
    assert exc.value.code == REFUSED_SIGNAL_AS_PERMISSION


def test_reception_without_suppression() -> None:
    signal = signal_from_fixture(_fixture("a0hm-desire-fixture"))
    received = apply_reception(signal)
    reception = received["reception"]
    assert isinstance(reception, dict)
    assert reception["received_without_suppression"] is True
    assert reception["fused_with_signal"] is False


def test_non_fusion_receipt_assertions() -> None:
    signal = signal_from_fixture(_fixture("a0hm-desire-fixture"))
    result = process_heart_mind_signal(signal)
    receipt = result.get("non_fusion_receipt")
    assert isinstance(receipt, dict)
    assertions = receipt.get("non_fusion_assertions", [])
    assert "signal_not_permission" in assertions
    assert "love_not_approval" not in assertions or "signal_not_authority" in assertions


def test_posture_snapshot_non_authority() -> None:
    snapshot = create_posture_snapshot(
        active_signal_refs=("a0hm:test",),
        active_route_refs=("ARB",),
        active_boundary_refs=("ARB",),
    )
    payload = snapshot["posture_snapshot"]
    assert isinstance(payload, dict)
    assert payload["authority_created"] is False


def test_secret_ingress_rejected() -> None:
    with pytest.raises(A0HmValidationError):
        signal_from_fixture(
            {
                "signal_id": "a0hm-secret",
                "source_type": "affective",
                "signal_summary": "api_key=leaked",
            }
        )


def test_forbidden_mint_phrase_rejected_at_ingress() -> None:
    with pytest.raises(A0HmValidationError):
        signal_from_fixture(
            {
                "signal_id": "a0hm-mint",
                "source_type": "affective",
                "signal_summary": "please mint gpp permit now",
            }
        )


def test_replay_determinism() -> None:
    fixtures = load_signal_fixtures()[:5]
    h1 = replay_fixture_stream(fixtures)
    h2 = replay_fixture_stream(fixtures)
    assert h1 == h2


def test_fixture_bundle_analysis_all_advisory() -> None:
    analysis = analyze_fixture_bundles()
    assert analysis["all_advisory"] is True
    assert analysis["bundle_count"] >= 12


def test_rtc_event_design_valid() -> None:
    ok, failures = validate_a0_hm_rtc_event_design(planned_a0_hm_event_refs())
    assert ok, failures


def test_record_hash_stable() -> None:
    signal = signal_from_fixture(_fixture("a0hm-desire-fixture"))
    h1 = signal.record_hash
    h2 = compute_record_hash(signal.to_payload(include_hash=False))
    assert h1 == h2
