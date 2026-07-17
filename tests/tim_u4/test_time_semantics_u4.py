"""CT-11 TIM-U4 stale authority time semantics tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from hg_core.admission.controller import AdmissionController
from hg_core.admission.ingress import reset_controller
from hg_core.admission.types import AdmissionRequest, ApprovalBinding
from hg_core.time.clock import FakeClock, format_rfc3339_z, reset_clock, set_clock
from hg_core.time.expiry import (
    STALE_APPROVAL,
    is_expired,
    validate_approval_window,
    validate_confirmation_window,
    validate_dry_run_window,
)
from hg_core.time.replay import evaluate_recorded_expiry, replay_independent_of_wall_clock
from hg_oea.dry_run import is_dry_run_stale
from hg_oea.types import DryRunResult
from hg_srp import create_maintenance_bundle, ingest_pytest_failure_artifact
from hg_srp.apply_verification import verify_approval_for_apply
from hg_srp.types import ChangeApprovalSignature, MaintenanceProposalBundle

NOW = "2026-06-12T15:00:00.000000Z"
EXPIRES = "2026-06-12T16:00:00.000000Z"
BEFORE = "2026-06-12T15:59:59.999000Z"
AT_BOUNDARY = "2026-06-12T16:00:00.000000Z"
FIXTURES = Path(__file__).parents[1] / "srp" / "fixtures"


@pytest.fixture(autouse=True)
def _reset_clocks() -> None:
    reset_clock()
    reset_controller()
    yield
    reset_clock()
    reset_controller()


def _bundle() -> MaintenanceProposalBundle:
    obs = ingest_pytest_failure_artifact(FIXTURES / "pytest_failure_sample.json", observed_at=NOW)
    return create_maintenance_bundle([obs], created_at=NOW)


def _approval(*, expires_at: str | None = EXPIRES) -> ChangeApprovalSignature:
    bundle = _bundle()
    return ChangeApprovalSignature(
        approval_id="appr-tim-u4",
        proposal_ref=bundle.bundle_id,
        bundle_hash=bundle.bundle_hash,
        approver="human:operator",
        decision="approved",
        decided_at=NOW,
        expires_at=expires_at,
    )


def test_tim_u4_approval_valid_before_boundary() -> None:
    bundle = _bundle()
    approval = _approval()
    result = verify_approval_for_apply(bundle, approval, bundle.bundle_hash, now=BEFORE)
    assert result.ok


def test_tim_u4_approval_refused_at_boundary() -> None:
    bundle = _bundle()
    approval = _approval()
    result = verify_approval_for_apply(bundle, approval, bundle.bundle_hash, now=AT_BOUNDARY)
    assert not result.ok
    assert result.reason_code == STALE_APPROVAL


def test_tim_u4_admission_refuses_stale_binding() -> None:
    clock = FakeClock()
    clock.set_utc(AT_BOUNDARY)
    set_clock(clock)
    ctrl = AdmissionController()
    decision = ctrl.request(
        AdmissionRequest(
            request_id="tim-stale",
            kind="srp_apply",
            idempotency_key="tim-stale",
            approval_binding=ApprovalBinding(
                proposal_hash="sha256:proposal",
                registry_hash="sha256:registry",
                expires_at=EXPIRES,
            ),
        )
    )
    assert not decision.admitted
    assert decision.reason_code == STALE_APPROVAL


def test_tim_u4_fake_clock_not_wall_flake() -> None:
    clock = FakeClock()
    clock.set_utc(BEFORE)
    set_clock(clock)
    ok, reason = validate_approval_window(EXPIRES, clock.now_utc())
    assert ok and reason == "ok"
    clock.advance_ms(1)
    ok2, reason2 = validate_approval_window(EXPIRES, clock.now_utc())
    assert not ok2 and reason2 == STALE_APPROVAL


def test_tim_u4_unknown_timestamp_fails_closed() -> None:
    assert is_expired("not-a-timestamp", NOW) is True
    ok, reason = validate_approval_window("bad", NOW)
    assert not ok and reason == STALE_APPROVAL


def test_tim_u4_final_confirmation_stale_refused() -> None:
    ok_before, reason_before = validate_confirmation_window(EXPIRES, BEFORE)
    assert ok_before and reason_before == "ok"
    ok_at, reason_at = validate_confirmation_window(EXPIRES, AT_BOUNDARY)
    assert not ok_at and reason_at == STALE_APPROVAL


def test_tim_u4_dry_run_window_and_hash_change() -> None:
    dry_run = DryRunResult(
        dry_run_id="dr-1",
        capability_id="local_report_file.write",
        input_hash="sha256:input-a",
        predicted_effect="write",
        touched_resources=(),
        risk_class="low",
        allowed=True,
        dry_run_hash="sha256:dr",
        created_at=NOW,
    )
    assert not is_dry_run_stale(
        dry_run,
        created_at=NOW,
        ttl_seconds=300,
        current_input_hash="sha256:input-a",
        now="2026-06-12T15:04:00.000000Z",
    )
    assert is_dry_run_stale(
        dry_run,
        created_at=NOW,
        ttl_seconds=300,
        current_input_hash="sha256:input-b",
        now="2026-06-12T15:04:00.000000Z",
    )
    ok, reason = validate_dry_run_window(
        dry_run_created_at=NOW,
        dry_run_input_hash="sha256:input-a",
        current_input_hash="sha256:input-a",
        now="2026-06-12T15:04:00.000000Z",
        ttl_seconds=300,
    )
    assert ok and reason == "ok"
    ok2, reason2 = validate_dry_run_window(
        dry_run_created_at=NOW,
        dry_run_input_hash="sha256:input-a",
        current_input_hash="sha256:input-a",
        now="2026-06-12T15:06:00.000000Z",
        ttl_seconds=300,
    )
    assert not ok2 and reason2 == "tim.refused.dry_run_expired"


def test_tim_u4_replay_uses_recorded_timestamp_only() -> None:
    clock = FakeClock()
    clock.set_utc(BEFORE)
    set_clock(clock)
    recorded = evaluate_recorded_expiry(expires_at=EXPIRES, recorded_now=BEFORE)
    assert recorded == (True, "ok")
    independent = replay_independent_of_wall_clock(
        expires_at=EXPIRES,
        recorded_now=BEFORE,
        advance_seconds=365 * 24 * 3600,
        clock_advance=clock.advance_seconds,
    )
    assert independent
    stale_recorded = evaluate_recorded_expiry(expires_at=EXPIRES, recorded_now=AT_BOUNDARY)
    assert stale_recorded == (False, STALE_APPROVAL)


def test_tim_u4_rfc3339_format() -> None:
    clock = FakeClock()
    stamp = clock.now_utc()
    assert stamp.endswith("Z")
    assert "." in stamp
