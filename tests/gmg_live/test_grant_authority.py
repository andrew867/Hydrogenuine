"""GMG-LIVE governed grant authority tests."""

from __future__ import annotations

import pytest

from hg_core.gmg_live.errors import (
    GMG_GRANT_CANDIDATE_BOUND,
    REFUSED_AMBIENT_GRANT,
    REFUSED_AUTHORITY_CONVERSION,
    REFUSED_EXPIRED_GRANT,
    REFUSED_MISSING_GPP_PERMIT,
    REFUSED_MISSING_IAM,
    REFUSED_MISSING_OPERATOR_APPROVAL,
    REFUSED_MISSING_TIM_FRESHNESS,
    REFUSED_MISSING_UEAK_ADMISSION,
    REFUSED_STALE_APPROVAL,
    REFUSED_STALE_TIM,
    GmgValidationError,
)
from hg_core.iam.registry import clear_registry_cache, load_registry
from hg_core.iam.types import reset_iam_event_ledger
from hg_runtime.grant_authority_live import (
    FIXTURE_CLOCK,
    FUTURE_EXPIRY,
    PAST_EXPIRY,
    PAST_GRANT_EXPIRY,
    analyze_gmg_fixtures,
    commit_to_fake_sink,
    load_gmg_fixtures,
    process_gmg_bundle,
    process_grant_authority,
    record_grant_expiry,
    refuse_grant_as_authority,
    replay_fixture_stream,
    request_from_fixture,
    request_to_fake_sink,
    revoke_grant,
    run_grant_authority_fixture,
    validate_grant_request,
)
from hg_runtime.grant_authority_live.types import GrantCandidate, GrantReceipt


@pytest.fixture(autouse=True)
def _reset_iam() -> None:
    clear_registry_cache()
    reset_iam_event_ledger()
    load_registry()


def _grant_fixture(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "request_id": "gmg-test-grant",
        "grant_type": "tool",
        "control_kind": "issue",
        "tool_ref": "tool:fixture:test",
        "operator_ref": "op:local",
        "freshness_ref": "tim:approval_window_ok",
        "approval_expires_at": FUTURE_EXPIRY,
        "grant_expires_at": FUTURE_EXPIRY,
        "scope": "approve_change",
        "requires_gpp": True,
        "requires_ueak": True,
        "gpp_permit_ref": "gpp:permit:test",
        "ueak_admission_ref": "ueak:admission:test",
        "rollback_plan_ref": "rollback:plan:test",
        "observed_at": FIXTURE_CLOCK,
    }
    base.update(overrides)
    return base


def test_valid_tool_grant_fixture_path() -> None:
    result = process_grant_authority(_grant_fixture(), observed_at=FIXTURE_CLOCK)
    assert result["status"] == "recorded"
    assert result["evidence_admissible"] is True
    assert result["permission_granted"] is False
    assert result["live_grant_performed"] is False
    assert result["committed_sink"]["live_grant_performed"] is False


def test_valid_namespace_grant() -> None:
    bundle = next(b for b in load_gmg_fixtures() if b["bundle_id"] == "gmg-valid-memory-namespace-grant")
    result = process_gmg_bundle(bundle, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "recorded"
    assert result["permission_granted"] is False


def test_valid_context_grant() -> None:
    bundle = next(b for b in load_gmg_fixtures() if b["bundle_id"] == "gmg-valid-context-grant")
    result = process_gmg_bundle(bundle, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "recorded"
    assert result["permission_granted"] is False


def test_valid_budget_grant() -> None:
    bundle = next(b for b in load_gmg_fixtures() if b["bundle_id"] == "gmg-valid-budget-grant")
    result = process_gmg_bundle(bundle, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "recorded"
    assert result["permission_granted"] is False


def test_missing_operator_approval_refusal() -> None:
    request = request_from_fixture(_grant_fixture(operator_ref=None))
    result = validate_grant_request(request, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == REFUSED_MISSING_OPERATOR_APPROVAL


def test_stale_approval_refusal() -> None:
    request = request_from_fixture(_grant_fixture(approval_expires_at=PAST_EXPIRY))
    result = validate_grant_request(request, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == REFUSED_STALE_APPROVAL


def test_missing_iam_refusal() -> None:
    request = request_from_fixture(_grant_fixture(operator_ref="bob"))
    result = validate_grant_request(request, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == REFUSED_MISSING_IAM


def test_missing_tim_freshness_refusal() -> None:
    request = request_from_fixture(_grant_fixture(freshness_ref="tim:missing"))
    result = validate_grant_request(request, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == REFUSED_MISSING_TIM_FRESHNESS


def test_stale_tim_refusal() -> None:
    request = request_from_fixture(_grant_fixture(freshness_ref="tim:stale"))
    result = validate_grant_request(request, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == REFUSED_STALE_TIM


def test_missing_gpp_permit_refusal() -> None:
    request = request_from_fixture(_grant_fixture(gpp_permit_ref=None))
    result = validate_grant_request(request, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == REFUSED_MISSING_GPP_PERMIT


def test_missing_ueak_admission_refusal() -> None:
    request = request_from_fixture(_grant_fixture(ueak_admission_ref=None))
    result = validate_grant_request(request, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == REFUSED_MISSING_UEAK_ADMISSION


def test_expired_grant_refusal() -> None:
    request = request_from_fixture(_grant_fixture(grant_expires_at=PAST_GRANT_EXPIRY))
    result = validate_grant_request(request, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == REFUSED_EXPIRED_GRANT


def test_ambient_grant_refusal() -> None:
    bundle = next(b for b in load_gmg_fixtures() if b["bundle_id"] == "gmg-ambient-grant")
    result = process_gmg_bundle(bundle, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == REFUSED_AMBIENT_GRANT


def test_authority_conversion_refusal() -> None:
    bundle = next(b for b in load_gmg_fixtures() if b["bundle_id"] == "gmg-authority-conversion")
    result = process_gmg_bundle(bundle, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "contained"
    assert result["reason_code"] == REFUSED_AUTHORITY_CONVERSION


def test_secret_redaction() -> None:
    with pytest.raises(GmgValidationError):
        request_from_fixture(_grant_fixture(tool_ref="password=secret123"))


def test_deterministic_replay_hash() -> None:
    bundles = list(load_gmg_fixtures()[:6])
    _, h1 = replay_fixture_stream(bundles, observed_at=FIXTURE_CLOCK)
    _, h2 = replay_fixture_stream(bundles, observed_at=FIXTURE_CLOCK)
    assert h1 == h2
    assert h1.startswith("sha256:")


def test_revocation_recorded() -> None:
    bundle = next(b for b in load_gmg_fixtures() if b["bundle_id"] == "gmg-valid-revoke")
    result = process_gmg_bundle(bundle, observed_at=FIXTURE_CLOCK)
    revocation = result.get("revocation_result")
    assert isinstance(revocation, dict)
    assert revocation.get("revocation_acknowledged") is True
    assert result["permission_granted"] is False


def test_no_out_of_scope_live_action() -> None:
    bundle = next(b for b in load_gmg_fixtures() if b["bundle_id"] == "gmg-out-of-scope-live")
    result = process_gmg_bundle(bundle, observed_at=FIXTURE_CLOCK)
    assert result["permission_granted"] is False
    assert result["live_action_performed"] is False
    assert result["live_grant_performed"] is False


def test_fake_sink_never_live_grant() -> None:
    candidate = GrantCandidate(
        candidate_id="gmg-cand-sink",
        request_id="gmg-req-sink",
        grant_type="tool",
        grant_target="tool:fixture:sink",
        operator_ref="op:local",
    )
    staged = request_to_fake_sink(candidate, observed_at=FIXTURE_CLOCK)
    assert staged["live_grant_performed"] is False
    assert staged["sink_type"] == "fake"
    receipt = GrantReceipt(
        receipt_id="gmg-rcpt-sink",
        request_id="gmg-req-sink",
        candidate_id="gmg-cand-sink",
        grant_type="tool",
        status="recorded",
        reason_code=GMG_GRANT_CANDIDATE_BOUND,
        operator_ref="op:local",
    )
    committed = commit_to_fake_sink(receipt, observed_at=FIXTURE_CLOCK)
    assert committed["live_grant_performed"] is False
    assert committed["sink_type"] == "fake"


def test_tep_wrapped_candidate() -> None:
    result = process_grant_authority(_grant_fixture(), observed_at=FIXTURE_CLOCK)
    tep = result.get("tep_wrapped")
    assert isinstance(tep, dict)
    candidate = result.get("candidate")
    assert isinstance(candidate, dict)
    assert candidate.get("authority_created") is False
    assert candidate.get("permission_granted") is False


def test_grant_adapter_fixture() -> None:
    adapter = run_grant_authority_fixture(observed_at=FIXTURE_CLOCK)
    assert adapter["live_grant_performed"] is False
    assert "tep_emission" in adapter


def test_refuse_grant_as_authority_raises() -> None:
    with pytest.raises(ValueError):
        refuse_grant_as_authority(treat_as_authority=True)


def test_analyze_fixtures_all_advisory() -> None:
    analysis = analyze_gmg_fixtures(observed_at=FIXTURE_CLOCK)
    assert analysis["all_advisory"] is True
    assert analysis["no_authority_created"] is True
    assert analysis["no_live_grants"] is True


def test_revoke_helper() -> None:
    receipt = GrantReceipt(
        receipt_id="gmg-rcpt-rev",
        request_id="gmg-req-rev",
        candidate_id="gmg-cand-rev",
        grant_type="tool",
        status="recorded",
        reason_code=GMG_GRANT_CANDIDATE_BOUND,
        operator_ref="op:local",
    )
    rv = revoke_grant(receipt, grant_target="tool:fixture:rev", observed_at=FIXTURE_CLOCK)
    assert rv["revocation_acknowledged"] is True
    assert rv["live_grant_performed"] is False


def test_expiry_helper() -> None:
    receipt = GrantReceipt(
        receipt_id="gmg-rcpt-exp",
        request_id="gmg-req-exp",
        candidate_id="gmg-cand-exp",
        grant_type="tool",
        status="recorded",
        reason_code=GMG_GRANT_CANDIDATE_BOUND,
        operator_ref="op:local",
    )
    exp = record_grant_expiry(
        receipt,
        grant_target="tool:fixture:exp",
        grant_expires_at=FUTURE_EXPIRY,
        observed_at=FIXTURE_CLOCK,
    )
    assert exp["live_grant_performed"] is False
    assert isinstance(exp.get("expiry_record"), dict)
