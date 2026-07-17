"""GXB Growth Expansion Boundary tests — fixture/static only."""

from __future__ import annotations

import pytest

from hg_core.gxb_cluster.errors import REFUSED_GXB_AS_AUTHORITY, REFUSED_STALE_INPUT, GxbValidationError
from hg_core.gxb_cluster.rtc_design import validate_gxb_rtc_event_design
from hg_core.policy_safety.hashing import compute_record_hash
from hg_core.gxb_cluster.events import planned_gxb_event_refs
from hg_runtime.growth_expansion_boundary import (
    FIXTURE_CLOCK,
    GrowthRequest,
    GrowthReceipt,
    GrowthPressureSignal,
    analyze_gxb_fixtures,
    classify_gxb_claim_risk,
    load_gxb_fixtures,
    process_gxb_bundle,
    refuse_gxb_as_authority,
    replay_fixture_stream,
    gxb_record_from_fixture,
)


def _record(**overrides: object) -> GrowthRequest:
    base = {"record_id": "gxb:req-test", "summary": "fixture test", "observed_at": FIXTURE_CLOCK, "classification": "stable"}
    base.update(overrides)
    return gxb_record_from_fixture(base)


def test_record_schema_non_authority() -> None:
    record = _record()
    payload = record.to_payload()
    assert payload["authority_created"] is False
    assert payload["permission_granted"] is False
    assert payload["growth_is_advisory_only"] is True


def test_record_rejects_authority_created() -> None:
    with pytest.raises(GxbValidationError):
        _record(authority_created=True)  # type: ignore[arg-type]


def test_record_rejects_permission_granted() -> None:
    with pytest.raises(GxbValidationError):
        _record(permission_granted=True)  # type: ignore[arg-type]


def test_signal_negative_proofs() -> None:
    signal = GrowthPressureSignal(signal_id="gxb:signal-test", pressure_score=0.2, observed_at=FIXTURE_CLOCK)
    payload = signal.to_payload()
    assert payload["permission_granted"] is False
    assert payload["authority_created"] is False


def test_receipt_negative_proofs() -> None:
    receipt = GrowthReceipt(receipt_id="gxb:receipt-test", record_ref="gxb:req-test", emitted_events=("GXB_RECORDED",))
    GrowthReceipt.validate_negative_proofs(receipt.to_payload())
    assert receipt.to_payload()["deletion_performed"] is False


def test_valid_bundle_recorded() -> None:
    bundle = next(b for b in load_gxb_fixtures() if b["bundle_id"] == "gxb-context-expansion")
    result = process_gxb_bundle(bundle)
    assert result["status"] == "recorded"
    assert result["permission_granted"] is False


def test_fail_closed_path() -> None:
    bundle = next(b for b in load_gxb_fixtures() if b["bundle_id"] == "gxb-stale-input")
    result = process_gxb_bundle(bundle)
    assert result["status"] in ("fail_closed", "contained")


def test_adversarial_contained() -> None:
    bundle = next(b for b in load_gxb_fixtures() if b["bundle_id"] == "gxb-growth-as-grant")
    result = process_gxb_bundle(bundle)
    assert result["status"] == "contained"
    assert result["permission_granted"] is False


def test_refuse_gxb_as_authority() -> None:
    with pytest.raises(GxbValidationError) as exc:
        refuse_gxb_as_authority(treat_as_authority=True)
    assert exc.value.code == REFUSED_GXB_AS_AUTHORITY


def test_deterministic_replay_hash() -> None:
    bundles = list(load_gxb_fixtures()[:5])
    _, hash_a = replay_fixture_stream(bundles)
    _, hash_b = replay_fixture_stream(bundles)
    assert hash_a == hash_b
    assert hash_a.startswith("sha256:")


def test_rtc_event_design() -> None:
    ok, failures = validate_gxb_rtc_event_design(planned_gxb_event_refs())
    assert ok, failures


def test_analyze_fixtures() -> None:
    analysis = analyze_gxb_fixtures()
    assert analysis["all_advisory"] is True
    assert analysis["no_authority_created"] is True
    assert int(analysis["bundle_count"]) >= 12


def test_record_hash_stability() -> None:
    record = _record()
    payload = record.to_payload(include_hash=False)
    assert record.record_hash == compute_record_hash(payload)


def test_growth_as_grant_refused() -> None:
    bundle = next(b for b in load_gxb_fixtures() if b["bundle_id"] == "gxb-growth-as-grant")
    result = process_gxb_bundle(bundle)
    assert result["status"] == "contained"
    assert result["permission_granted"] is False


def test_agent_spawn_refused() -> None:
    bundle = next(b for b in load_gxb_fixtures() if b["bundle_id"] == "gxb-agent-spawn")
    result = process_gxb_bundle(bundle)
    assert result["status"] == "contained"
    assert result["permission_granted"] is False


def test_tool_grant_refused() -> None:
    bundle = next(b for b in load_gxb_fixtures() if b["bundle_id"] == "gxb-tool-grant")
    result = process_gxb_bundle(bundle)
    assert result["status"] == "contained"
    assert result["permission_granted"] is False


def test_budget_grant_refused() -> None:
    bundle = next(b for b in load_gxb_fixtures() if b["bundle_id"] == "gxb-budget-grant")
    result = process_gxb_bundle(bundle)
    assert result["status"] == "contained"
    assert result["permission_granted"] is False


def test_authority_conversion_refused() -> None:
    bundle = next(b for b in load_gxb_fixtures() if b["bundle_id"] == "gxb-authority-conversion")
    result = process_gxb_bundle(bundle)
    assert result["status"] == "contained"
    assert result["permission_granted"] is False


def test_positive_gxb_context_expansion() -> None:
    bundle = next(b for b in load_gxb_fixtures() if b["bundle_id"] == "gxb-context-expansion")
    result = process_gxb_bundle(bundle)
    assert result["status"] == "recorded"
    assert result["permission_granted"] is False


def test_positive_gxb_memory_namespace() -> None:
    bundle = next(b for b in load_gxb_fixtures() if b["bundle_id"] == "gxb-memory-namespace")
    result = process_gxb_bundle(bundle)
    assert result["status"] == "recorded"
    assert result["permission_granted"] is False


def test_positive_gxb_tool_grant_proposal() -> None:
    bundle = next(b for b in load_gxb_fixtures() if b["bundle_id"] == "gxb-tool-grant-proposal")
    result = process_gxb_bundle(bundle)
    assert result["status"] == "recorded"
    assert result["permission_granted"] is False


