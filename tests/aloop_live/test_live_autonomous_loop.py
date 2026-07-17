"""ALOOP-LIVE governed autonomous loop supervisor tests."""

from __future__ import annotations

import pytest

from hg_core.aloop_live.errors import (
    ALOOP_LEASE_BOUND,
    REFUSED_AUTHORITY_CONVERSION,
    REFUSED_BUDGET_EXCEEDED,
    REFUSED_HEARTBEAT_STALE,
    REFUSED_KILL_SWITCH,
    REFUSED_LEASE_EXPIRED,
    REFUSED_MISSING_IAM,
    REFUSED_MISSING_OPERATOR_APPROVAL,
    REFUSED_MISSING_TIM_FRESHNESS,
    REFUSED_PANIC_LOCKDOWN,
    REFUSED_SELF_RENEWAL,
    REFUSED_STALE_APPROVAL,
    AloopValidationError,
)
from hg_core.iam.registry import clear_registry_cache, load_registry
from hg_core.iam.types import reset_iam_event_ledger
from hg_runtime.live_autonomous_loop import (
    FIXTURE_CLOCK,
    FUTURE_EXPIRY,
    FUTURE_LEASE,
    PAST_EXPIRY,
    PAST_LEASE,
    LoopLease,
    LoopSupervisorReceipt,
    analyze_aloop_fixtures,
    lease_to_fake_sink,
    load_aloop_fixtures,
    process_aloop_bundle,
    process_autonomous_loop,
    refuse_aloop_as_authority,
    replay_fixture_stream,
    request_from_fixture,
    rollback_loop_supervisor,
    run_autonomous_loop_fixture,
    supervise_to_fake_sink,
    validate_loop_request,
)


@pytest.fixture(autouse=True)
def _reset_iam() -> None:
    clear_registry_cache()
    reset_iam_event_ledger()
    load_registry()


def _loop_fixture(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "request_id": "aloop-test-loop",
        "loop_scope": "loop:fixture:observe",
        "lease_expires_at": FUTURE_LEASE,
        "heartbeat_ref": "hrt:heartbeat:fresh",
        "budget_ref": "budget:fixture:ok",
        "operator_ref": "op:local",
        "freshness_ref": "tim:approval_window_ok",
        "approval_expires_at": FUTURE_EXPIRY,
        "scope": "approve_change",
        "rollback_plan_ref": "rollback:plan:test",
        "observed_at": FIXTURE_CLOCK,
    }
    base.update(overrides)
    return base


def test_valid_supervise_fixture_path() -> None:
    result = process_autonomous_loop(_loop_fixture(), observed_at=FIXTURE_CLOCK)
    assert result["status"] == "recorded"
    assert result["evidence_admissible"] is True
    assert result["permission_granted"] is False
    assert result["live_loop_started"] is False
    assert result["loop_self_renewed"] is False
    assert result["committed_sink"]["live_loop_started"] is False


def test_missing_operator_approval_refusal() -> None:
    request = request_from_fixture(_loop_fixture(operator_ref=None))
    result = validate_loop_request(request, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == REFUSED_MISSING_OPERATOR_APPROVAL


def test_stale_approval_refusal() -> None:
    request = request_from_fixture(_loop_fixture(approval_expires_at=PAST_EXPIRY))
    result = validate_loop_request(request, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == REFUSED_STALE_APPROVAL


def test_missing_iam_refusal() -> None:
    request = request_from_fixture(_loop_fixture(operator_ref="bob"))
    result = validate_loop_request(request, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == REFUSED_MISSING_IAM


def test_missing_tim_freshness_refusal() -> None:
    request = request_from_fixture(_loop_fixture(freshness_ref="tim:missing"))
    result = validate_loop_request(request, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == REFUSED_MISSING_TIM_FRESHNESS


def test_lease_expired_refusal() -> None:
    request = request_from_fixture(_loop_fixture(lease_expires_at=PAST_LEASE))
    result = validate_loop_request(request, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == REFUSED_LEASE_EXPIRED


def test_heartbeat_stale_refusal() -> None:
    request = request_from_fixture(_loop_fixture(heartbeat_ref="hrt:heartbeat:stale"))
    result = validate_loop_request(request, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == REFUSED_HEARTBEAT_STALE


def test_budget_exceeded_refusal() -> None:
    request = request_from_fixture(_loop_fixture(budget_ref="budget:exceeded"))
    result = validate_loop_request(request, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == REFUSED_BUDGET_EXCEEDED


def test_kill_switch_refusal() -> None:
    request = request_from_fixture(_loop_fixture(kill_switch_engaged=True))
    result = validate_loop_request(request, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == REFUSED_KILL_SWITCH


def test_panic_lockdown_refusal() -> None:
    request = request_from_fixture(_loop_fixture(panic_lockdown=True))
    result = validate_loop_request(request, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == REFUSED_PANIC_LOCKDOWN


def test_self_renewal_refusal() -> None:
    bundle = next(b for b in load_aloop_fixtures() if b["bundle_id"] == "aloop-self-renewal")
    result = process_aloop_bundle(bundle, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "contained"
    assert result["reason_code"] == REFUSED_SELF_RENEWAL


def test_authority_conversion_refusal() -> None:
    bundle = next(b for b in load_aloop_fixtures() if b["bundle_id"] == "aloop-authority-conversion")
    result = process_aloop_bundle(bundle, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "contained"
    assert result["reason_code"] == REFUSED_AUTHORITY_CONVERSION


def test_secret_redaction() -> None:
    with pytest.raises(AloopValidationError):
        request_from_fixture(_loop_fixture(loop_scope="password=secret123"))


def test_deterministic_replay_hash() -> None:
    bundles = list(load_aloop_fixtures()[:8])
    _, h1 = replay_fixture_stream(bundles, observed_at=FIXTURE_CLOCK)
    _, h2 = replay_fixture_stream(bundles, observed_at=FIXTURE_CLOCK)
    assert h1 == h2
    assert h1.startswith("sha256:")


def test_rollback_recorded() -> None:
    bundle = next(b for b in load_aloop_fixtures() if b["bundle_id"] == "aloop-valid-rollback")
    result = process_aloop_bundle(bundle, observed_at=FIXTURE_CLOCK)
    rollback = result.get("rollback_result")
    assert isinstance(rollback, dict)
    assert rollback.get("rollback_acknowledged") is True
    assert result["live_loop_started"] is False


def test_pause_without_live_loop() -> None:
    bundle = next(b for b in load_aloop_fixtures() if b["bundle_id"] == "aloop-pause-requested")
    result = process_aloop_bundle(bundle, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "recorded"
    assert isinstance(result.get("pause_result"), dict)
    assert result["live_loop_started"] is False


def test_fake_sink_never_live() -> None:
    lease = LoopLease(
        lease_id="aloop-lease-test",
        request_id="aloop-req-test",
        loop_scope="loop:fixture:test",
        lease_expires_at=FUTURE_LEASE,
        heartbeat_ref="hrt:heartbeat:fresh",
        budget_ref="budget:fixture:ok",
        operator_ref="op:local",
    )
    staged = lease_to_fake_sink(lease, observed_at=FIXTURE_CLOCK)
    assert staged["live_loop_started"] is False
    receipt = LoopSupervisorReceipt(
        receipt_id="aloop-rcpt-sink",
        request_id="aloop-req-sink",
        lease_id="aloop-lease-test",
        supervisor_state="supervised",
        status="recorded",
        reason_code=ALOOP_LEASE_BOUND,
        operator_ref="op:local",
    )
    committed = supervise_to_fake_sink(receipt, observed_at=FIXTURE_CLOCK)
    assert committed["live_loop_started"] is False
    assert committed["sink_type"] == "fake"


def test_tep_wrapped_lease() -> None:
    result = process_autonomous_loop(_loop_fixture(), observed_at=FIXTURE_CLOCK)
    tep = result.get("tep_wrapped")
    assert isinstance(tep, dict)
    receipt = result.get("receipt")
    assert isinstance(receipt, dict)
    assert receipt.get("authority_created") is False
    assert receipt.get("live_loop_started") is False


def test_loop_adapter_fixture() -> None:
    adapter = run_autonomous_loop_fixture(observed_at=FIXTURE_CLOCK)
    assert adapter["live_loop_started"] is False
    assert "tep_emission" in adapter


def test_refuse_loop_as_authority_raises() -> None:
    with pytest.raises(ValueError):
        refuse_aloop_as_authority(treat_as_authority=True)


def test_analyze_fixtures_all_advisory() -> None:
    analysis = analyze_aloop_fixtures(observed_at=FIXTURE_CLOCK)
    assert analysis["all_advisory"] is True
    assert analysis["no_authority_created"] is True
    assert analysis["no_live_loop"] is True
    assert analysis["no_self_renewal"] is True


def test_rollback_helper() -> None:
    receipt = LoopSupervisorReceipt(
        receipt_id="aloop-rcpt-rbk",
        request_id="aloop-req-rbk",
        lease_id="aloop-lease-rbk",
        supervisor_state="supervised",
        status="recorded",
        reason_code=ALOOP_LEASE_BOUND,
        operator_ref="op:local",
    )
    rb = rollback_loop_supervisor(receipt, observed_at=FIXTURE_CLOCK)
    assert rb["rollback_acknowledged"] is True
    assert rb["live_loop_started"] is False
