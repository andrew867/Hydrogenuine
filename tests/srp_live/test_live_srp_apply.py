"""SRP-LIVE governed SRP apply tests."""

from __future__ import annotations

import pytest

from hg_core.iam.registry import clear_registry_cache, load_registry
from hg_core.iam.types import reset_iam_event_ledger
from hg_core.srp_live.decide import srp_apply_decide
from hg_core.srp_live.errors import (
    APPLY_FAKE,
    APPLY_FAKE_OK,
    REJECT_DIGEST_MISMATCH,
    REJECT_NO_PERMIT,
    REJECT_PANIC_LOCKDOWN,
    REFUSED_AUTHORITY_CONVERSION,
    REFUSED_MISSING_IAM,
    REFUSED_MISSING_OPERATOR_APPROVAL,
    REFUSED_MISSING_TIM_FRESHNESS,
    REFUSED_SELF_MODIFICATION,
    REFUSED_STALE_APPROVAL,
    ROUTE_TO_CHANGE_CONTROL,
    SRP_COMMIT_FAKE_SINK,
    SrpValidationError,
)
from hg_runtime.live_srp_apply import (
    FIXTURE_CLOCK,
    FUTURE_EXPIRY,
    PAST_EXPIRY,
    analyze_srp_fixtures,
    apply_to_fake_sink,
    load_srp_fixtures,
    plan_to_operator_visible,
    process_srp_apply,
    process_srp_bundle,
    refuse_srp_as_authority,
    replay_fixture_stream,
    request_from_fixture,
    reset_idempotency_cache,
    rollback_srp_apply,
    run_srp_apply_fixture,
    validate_srp_apply_request,
)
from hg_runtime.live_srp_apply.types import SRPApplyReceipt, SRPApplyRequest


@pytest.fixture(autouse=True)
def _reset_state() -> None:
    clear_registry_cache()
    reset_iam_event_ledger()
    load_registry()
    reset_idempotency_cache()


def _apply_fixture(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "repair_id": "srp-test-apply",
        "target_ref": "target:repo:test",
        "change_set_digest": "digest:test-approved",
        "approved_digest": "digest:test-approved",
        "sandbox_proof_ref": "sandbox:proof:fresh",
        "approval_receipt_ref": "approval:receipt:signed",
        "operator_ref": "op:local",
        "freshness_ref": "tim:approval_window_ok",
        "approval_expires_at": FUTURE_EXPIRY,
        "scope": "approve_change",
        "tep_envelope_ref": "tep:envelope:test",
        "rollback_plan_ref": "rollback:plan:test",
        "gpp_permit_ref": "gpp:permit:test",
        "ueak_admission_ref": "ueak:admission:test",
        "observed_at": FIXTURE_CLOCK,
    }
    base.update(overrides)
    return base


def _permit_binding(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "binding_id": "bind:srp-test-apply",
        "repair_id": "srp-test-apply",
        "gpp_permit_ref": "gpp:permit:test",
        "ueak_admission_ref": "ueak:admission:test",
    }
    base.update(overrides)
    return base


def _change_control(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "approval_signed": True,
        "sandbox_proof_stale": False,
        "bac_laundering": False,
    }
    base.update(overrides)
    return base


def test_valid_apply_fixture_path() -> None:
    result = process_srp_apply(
        _apply_fixture(),
        permit_binding_data=_permit_binding(),
        change_control_state=_change_control(),
        observed_at=FIXTURE_CLOCK,
    )
    assert result["status"] == "recorded"
    assert result["apply_performed"] is True
    assert result["evidence_admissible"] is True
    assert result["permission_granted"] is False
    assert result["live_landing_performed"] is False
    assert result["applied_sink"]["live_landing_performed"] is False
    receipt = result["receipt"]
    assert isinstance(receipt, dict)
    assert receipt["outcome"] == APPLY_FAKE_OK


def test_plan_apply_separation() -> None:
    result = process_srp_apply(
        _apply_fixture(),
        permit_binding_data=_permit_binding(),
        change_control_state=_change_control(),
        observed_at=FIXTURE_CLOCK,
    )
    plan_result = result.get("plan_result")
    assert isinstance(plan_result, dict)
    assert plan_result.get("phase") == "plan"
    assert result.get("phase_completed") == "apply"
    plan = plan_result.get("plan")
    assert isinstance(plan, dict)
    assert plan.get("operator_visible") is True
    assert plan.get("phase") == "plan"


def test_missing_operator_approval_refusal() -> None:
    request = request_from_fixture(_apply_fixture(operator_ref=None))
    result = validate_srp_apply_request(request, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == REFUSED_MISSING_OPERATOR_APPROVAL


def test_stale_approval_refusal() -> None:
    request = request_from_fixture(_apply_fixture(approval_expires_at=PAST_EXPIRY))
    result = validate_srp_apply_request(request, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == REFUSED_STALE_APPROVAL


def test_missing_iam_refusal() -> None:
    request = request_from_fixture(_apply_fixture(operator_ref="bob"))
    result = validate_srp_apply_request(request, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == REFUSED_MISSING_IAM


def test_missing_tim_freshness_refusal() -> None:
    request = request_from_fixture(_apply_fixture(freshness_ref="tim:missing"))
    result = validate_srp_apply_request(request, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == REFUSED_MISSING_TIM_FRESHNESS


def test_srp_apply_decide_missing_permit() -> None:
    decision = srp_apply_decide(
        request=_apply_fixture(),
        permit_binding={"gpp_permit_ref": None, "ueak_admission_ref": "ueak:admission:test"},
        admission_token={"ueak_admission_ref": "ueak:admission:test"},
        change_control_state=_change_control(),
    )
    assert decision["decision"] == REJECT_NO_PERMIT


def test_srp_apply_decide_panic_lockdown() -> None:
    decision = srp_apply_decide(
        request=_apply_fixture(),
        permit_binding=_permit_binding(),
        admission_token={"ueak_admission_ref": "ueak:admission:test"},
        change_control_state=_change_control(),
        boundary_liveness_state={"panic_lockdown": True},
    )
    assert decision["decision"] == REJECT_PANIC_LOCKDOWN


def test_srp_apply_decide_route_stale_approval() -> None:
    decision = srp_apply_decide(
        request=_apply_fixture(),
        permit_binding=_permit_binding(),
        admission_token={"ueak_admission_ref": "ueak:admission:test"},
        change_control_state={"approval_stale": True},
    )
    assert decision["decision"] == ROUTE_TO_CHANGE_CONTROL


def test_srp_apply_decide_apply_fake() -> None:
    decision = srp_apply_decide(
        request=_apply_fixture(),
        permit_binding=_permit_binding(),
        admission_token={"ueak_admission_ref": "ueak:admission:test"},
        change_control_state=_change_control(),
    )
    assert decision["decision"] == APPLY_FAKE
    assert decision["live_landing_performed"] is False


def test_digest_mismatch_reject() -> None:
    decision = srp_apply_decide(
        request=_apply_fixture(change_set_digest="digest:drifted"),
        permit_binding=_permit_binding(),
        admission_token={"ueak_admission_ref": "ueak:admission:test"},
        change_control_state=_change_control(),
    )
    assert decision["decision"] == REJECT_DIGEST_MISMATCH


def test_self_modification_refusal() -> None:
    with pytest.raises(SrpValidationError):
        request_from_fixture(_apply_fixture(self_approved=True))


def test_authority_conversion_refusal() -> None:
    bundle = next(b for b in load_srp_fixtures() if b["bundle_id"] == "srp-authority-conversion")
    result = process_srp_bundle(bundle, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "contained"
    assert result["reason_code"] == REFUSED_AUTHORITY_CONVERSION


def test_secret_redaction() -> None:
    with pytest.raises(SrpValidationError):
        request_from_fixture(_apply_fixture(target_ref="password=secret123"))


def test_deterministic_replay_hash() -> None:
    bundles = list(load_srp_fixtures()[:8])
    _, h1 = replay_fixture_stream(bundles, observed_at=FIXTURE_CLOCK)
    _, h2 = replay_fixture_stream(bundles, observed_at=FIXTURE_CLOCK)
    assert h1 == h2
    assert h1.startswith("sha256:")


def test_rollback_recorded() -> None:
    bundle = next(b for b in load_srp_fixtures() if b["bundle_id"] == "srp-valid-rollback")
    result = process_srp_bundle(bundle, observed_at=FIXTURE_CLOCK)
    rollback = result.get("rollback_result")
    assert isinstance(rollback, dict)
    assert rollback.get("rollback_acknowledged") is True
    assert result["live_landing_performed"] is False


def test_fake_sink_never_live() -> None:
    request = request_from_fixture(_apply_fixture())
    plan = plan_to_operator_visible(request, observed_at=FIXTURE_CLOCK)
    assert plan["phase"] == "plan"
    assert plan["live_landing_performed"] is False
    receipt = SRPApplyReceipt(
        receipt_id="srp-rcpt-sink",
        repair_id="srp-test-apply",
        outcome=APPLY_FAKE_OK,
        permit_ref="gpp:permit:test",
        admission_ref="ueak:admission:test",
        approved_digest="digest:test-approved",
        applied_digest="digest:test-approved",
        sandbox_proof_ref="sandbox:proof:fresh",
        operator_ref="op:local",
    )
    applied = apply_to_fake_sink(receipt, observed_at=FIXTURE_CLOCK)
    assert applied["live_landing_performed"] is False
    assert applied["sink_type"] == "fake"


def test_tep_wrapped_plan() -> None:
    result = process_srp_apply(
        _apply_fixture(),
        permit_binding_data=_permit_binding(),
        change_control_state=_change_control(),
        observed_at=FIXTURE_CLOCK,
    )
    tep = result.get("tep_wrapped")
    assert isinstance(tep, dict)
    receipt = result.get("receipt")
    assert isinstance(receipt, dict)
    assert receipt.get("authority_created") is False
    assert receipt.get("live_landing_performed") is False


def test_apply_adapter_fixture() -> None:
    adapter = run_srp_apply_fixture(observed_at=FIXTURE_CLOCK)
    assert adapter["live_landing_performed"] is False
    assert "tep_emission" in adapter


def test_refuse_srp_as_authority_raises() -> None:
    with pytest.raises(ValueError):
        refuse_srp_as_authority(treat_as_authority=True)


def test_analyze_fixtures_all_advisory() -> None:
    analysis = analyze_srp_fixtures(observed_at=FIXTURE_CLOCK)
    assert analysis["all_advisory"] is True
    assert analysis["no_authority_created"] is True
    assert analysis["no_live_landing"] is True


def test_rollback_helper() -> None:
    receipt = SRPApplyReceipt(
        receipt_id="srp-rcpt-rbk",
        repair_id="srp-repair-rbk",
        outcome=APPLY_FAKE_OK,
        permit_ref="gpp:permit:test",
        admission_ref="ueak:admission:test",
        approved_digest="digest:test",
        applied_digest="digest:test",
        sandbox_proof_ref="sandbox:proof:fresh",
        operator_ref="op:local",
    )
    rb = rollback_srp_apply(
        receipt,
        target_ref="target:repo:rbk",
        prior_digest="digest:prior",
        observed_at=FIXTURE_CLOCK,
    )
    assert rb["rollback_acknowledged"] is True
    assert rb["live_landing_performed"] is False


def test_idempotency_dedupe() -> None:
    fixture = _apply_fixture(idempotency_key="idem:srp:test-1")
    r1 = process_srp_apply(
        fixture,
        permit_binding_data=_permit_binding(),
        change_control_state=_change_control(),
        observed_at=FIXTURE_CLOCK,
    )
    r2 = process_srp_apply(
        fixture,
        permit_binding_data=_permit_binding(),
        change_control_state=_change_control(),
        observed_at=FIXTURE_CLOCK,
    )
    assert r2.get("idempotent_replay") is True
    assert r1.get("receipt") == r2.get("receipt")


def test_panic_lockdown_bundle() -> None:
    bundle = next(b for b in load_srp_fixtures() if b["bundle_id"] == "srp-panic-lockdown")
    result = process_srp_bundle(bundle, observed_at=FIXTURE_CLOCK)
    decision = result.get("decision")
    assert isinstance(decision, dict)
    assert decision.get("decision") == REJECT_PANIC_LOCKDOWN
    assert result["live_landing_performed"] is False


def test_receipt_stable_hash() -> None:
    request = SRPApplyRequest(
        repair_id="srp-hash-test",
        target_ref="target:repo:hash",
        change_set_digest="digest:hash",
        approved_digest="digest:hash",
        sandbox_proof_ref="sandbox:proof:hash",
        approval_receipt_ref="approval:receipt:hash",
        operator_ref="op:local",
        freshness_ref="tim:approval_window_ok",
        approval_expires_at=FUTURE_EXPIRY,
        tep_envelope_ref="tep:envelope:hash",
        rollback_plan_ref="rollback:plan:hash",
        scope="approve_change",
    )
    p1 = request.to_payload()
    p2 = request.to_payload()
    assert p1["record_hash"] == p2["record_hash"]
    assert p1["srp_apply_called"] is False
    assert p1["live_landing_performed"] is False
