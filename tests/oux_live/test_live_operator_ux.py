"""OUX-LIVE governed live operator review console tests."""

from __future__ import annotations

import pytest

from hg_core.iam.registry import clear_registry_cache, load_registry
from hg_core.iam.types import reset_iam_event_ledger
from hg_core.oux_live.errors import (
    OUX_APPROVAL_EVIDENCE_BOUND,
    REFUSED_AUTHORITY_CONVERSION,
    REFUSED_MISSING_GPP_PERMIT,
    REFUSED_MISSING_IAM,
    REFUSED_MISSING_OPERATOR_APPROVAL,
    REFUSED_MISSING_TIM_FRESHNESS,
    REFUSED_MISSING_UEAK_ADMISSION,
    REFUSED_PANIC_AS_PERMISSION,
    REFUSED_STALE_APPROVAL,
    REFUSED_STALE_TIM,
    OuxValidationError,
)
from hg_runtime.live_operator_ux import (
    FIXTURE_CLOCK,
    FUTURE_EXPIRY,
    PAST_EXPIRY,
    action_request_from_fixture,
    analyze_oux_fixtures,
    audit_operator_ux_events,
    dispatch_to_fake_sink,
    load_oux_fixtures,
    process_operator_control,
    process_oux_bundle,
    refuse_oux_as_authority,
    render_review_queue_view,
    replay_fixture_stream,
    run_console_adapter_fixture,
    validate_operator_action_request,
)
from hg_runtime.live_operator_ux.types import OperatorUXReceipt


@pytest.fixture(autouse=True)
def _reset_iam() -> None:
    clear_registry_cache()
    reset_iam_event_ledger()
    load_registry()


def _approve_fixture(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "request_id": "oux-test-approve",
        "review_item_ref": "ori-item:test",
        "control_kind": "approve",
        "operator_ref": "op:local",
        "freshness_ref": "tim:approval_window_ok",
        "approval_expires_at": FUTURE_EXPIRY,
        "scope": "approve_change",
        "observed_at": FIXTURE_CLOCK,
    }
    base.update(overrides)
    return base


def test_valid_approved_fixture_path() -> None:
    request = action_request_from_fixture(_approve_fixture())
    result = process_operator_control(request, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "recorded"
    assert result["reason_code"] == OUX_APPROVAL_EVIDENCE_BOUND
    assert result["evidence_admissible"] is True
    assert result["permission_granted"] is False
    assert result["fake_sink"]["live_action_performed"] is False


def test_missing_operator_approval_refusal() -> None:
    request = action_request_from_fixture(_approve_fixture(operator_ref=None))
    result = validate_operator_action_request(request, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == REFUSED_MISSING_OPERATOR_APPROVAL


def test_stale_approval_refusal() -> None:
    request = action_request_from_fixture(_approve_fixture(approval_expires_at=PAST_EXPIRY))
    result = validate_operator_action_request(request, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == REFUSED_STALE_APPROVAL


def test_missing_iam_refusal() -> None:
    request = action_request_from_fixture(_approve_fixture(operator_ref="bob"))
    result = validate_operator_action_request(request, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == REFUSED_MISSING_IAM


def test_missing_tim_freshness_refusal() -> None:
    request = action_request_from_fixture(_approve_fixture(freshness_ref="tim:missing"))
    result = validate_operator_action_request(request, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == REFUSED_MISSING_TIM_FRESHNESS


def test_stale_tim_refusal() -> None:
    request = action_request_from_fixture(_approve_fixture(freshness_ref="tim:stale"))
    result = validate_operator_action_request(request, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == REFUSED_STALE_TIM


def test_missing_gpp_permit_refusal() -> None:
    request = action_request_from_fixture(_approve_fixture(requires_gpp=True))
    result = validate_operator_action_request(request, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == REFUSED_MISSING_GPP_PERMIT


def test_missing_ueak_admission_refusal() -> None:
    request = action_request_from_fixture(_approve_fixture(requires_ueak=True))
    result = validate_operator_action_request(request, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == REFUSED_MISSING_UEAK_ADMISSION


def test_authority_conversion_refusal() -> None:
    bundle = next(b for b in load_oux_fixtures() if b["bundle_id"] == "oux-authority-conversion")
    result = process_oux_bundle(bundle, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "contained"
    assert result["reason_code"] == REFUSED_AUTHORITY_CONVERSION


def test_secret_redaction() -> None:
    with pytest.raises(OuxValidationError):
        action_request_from_fixture(_approve_fixture(review_item_ref="password=secret123"))


def test_deterministic_replay_hash() -> None:
    bundles = list(load_oux_fixtures()[:6])
    _, h1 = replay_fixture_stream(bundles, observed_at=FIXTURE_CLOCK)
    _, h2 = replay_fixture_stream(bundles, observed_at=FIXTURE_CLOCK)
    assert h1 == h2
    assert h1.startswith("sha256:")


def test_panic_kill_switch_recorded() -> None:
    request = action_request_from_fixture(
        _approve_fixture(request_id="oux-panic", control_kind="panic", review_item_ref="ori-item:panic")
    )
    result = process_operator_control(request, observed_at=FIXTURE_CLOCK)
    receipt = result["receipt"]
    assert receipt["kill_switch_active"] is True
    assert result["permission_granted"] is False


def test_panic_as_permission_refused() -> None:
    bundle = next(b for b in load_oux_fixtures() if b["bundle_id"] == "oux-panic-as-permission")
    result = process_oux_bundle(bundle, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "contained"
    assert result["reason_code"] == REFUSED_PANIC_AS_PERMISSION


def test_no_out_of_scope_live_action() -> None:
    bundle = next(b for b in load_oux_fixtures() if b["bundle_id"] == "oux-out-of-scope-live")
    result = process_oux_bundle(bundle, observed_at=FIXTURE_CLOCK)
    assert result["permission_granted"] is False
    assert result["live_action_performed"] is False


def test_fake_sink_never_live() -> None:
    receipt = OperatorUXReceipt(
        receipt_id="oux-rcpt-sink",
        request_id="oux-req-sink",
        control_kind="approve",
        status="recorded",
        reason_code=OUX_APPROVAL_EVIDENCE_BOUND,
        operator_ref="op:local",
    )
    sink = dispatch_to_fake_sink(receipt, observed_at=FIXTURE_CLOCK)
    assert sink["live_action_performed"] is False
    assert sink["sink_type"] == "fake"


def test_queue_view_not_approval() -> None:
    view = render_review_queue_view(observed_at=FIXTURE_CLOCK)
    assert view["digest_is_not_approval"] is True
    assert view["permission_granted"] is False


def test_audit_log_output() -> None:
    audit = audit_operator_ux_events(observed_at=FIXTURE_CLOCK)
    assert audit["passive_audit_only"] is True
    assert audit["event_count"] >= 14


def test_console_adapter_fixture() -> None:
    adapter = run_console_adapter_fixture(observed_at=FIXTURE_CLOCK)
    assert adapter["live_action_performed"] is False
    assert "tep_emission" in adapter


def test_refuse_oux_as_authority_raises() -> None:
    with pytest.raises(ValueError):
        refuse_oux_as_authority(treat_as_authority=True)


def test_analyze_fixtures_all_advisory() -> None:
    analysis = analyze_oux_fixtures(observed_at=FIXTURE_CLOCK)
    assert analysis["all_advisory"] is True
    assert analysis["no_authority_created"] is True
