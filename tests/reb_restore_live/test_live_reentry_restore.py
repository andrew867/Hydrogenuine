"""REB-RESTORE-LIVE governed live reentry restore tests."""

from __future__ import annotations

import pytest

from hg_core.iam.registry import clear_registry_cache, load_registry
from hg_core.iam.types import reset_iam_event_ledger
from hg_core.reb_restore_live.errors import (
    REB_RESTORE_CANDIDATE_BOUND,
    RebRestoreValidationError,
    REFUSED_AUTHORITY_CONVERSION,
    REFUSED_IDENTITY_OVERCLAIM,
    REFUSED_MISSING_GPP_PERMIT,
    REFUSED_MISSING_IAM,
    REFUSED_MISSING_OPERATOR_APPROVAL,
    REFUSED_MISSING_ROLLBACK_PLAN,
    REFUSED_MISSING_TIM_FRESHNESS,
    REFUSED_MISSING_UEAK_ADMISSION,
    REFUSED_REVOKED_PERMIT,
    REFUSED_STALE_APPROVAL,
    REFUSED_STALE_MEMORY_CLAIM,
    REFUSED_STALE_TIM,
)
from hg_runtime.live_reentry_restore import (
    FIXTURE_CLOCK,
    FUTURE_EXPIRY,
    PAST_EXPIRY,
    analyze_reb_restore_fixtures,
    commit_to_fake_sink,
    continuity_refusal_record,
    load_reb_restore_fixtures,
    process_checkpoint_restore,
    process_reb_restore_bundle,
    refuse_reb_as_authority,
    replay_fixture_stream,
    request_from_fixture,
    run_reentry_restore_fixture,
    stage_to_fake_sink,
    validate_checkpoint_restore_request,
)
from hg_runtime.live_reentry_restore.types import RestoreCandidate, RestoreReceipt


@pytest.fixture(autouse=True)
def _reset_iam() -> None:
    clear_registry_cache()
    reset_iam_event_ledger()
    load_registry()


def _restore_fixture(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "request_id": "reb-restore-test",
        "restore_kind": "checkpoint",
        "checkpoint_digest": "digest:test",
        "operator_ref": "op:local",
        "freshness_ref": "tim:approval_window_ok",
        "approval_expires_at": FUTURE_EXPIRY,
        "scope": "approve_change",
        "checkpoint_ref": "checkpoint:test",
        "continuity_policy_ref": "continuity:policy:test",
        "rollback_plan_ref": "rollback:plan:test",
        "observed_at": FIXTURE_CLOCK,
    }
    base.update(overrides)
    return base


def test_valid_restore_fixture_path() -> None:
    result = process_checkpoint_restore(_restore_fixture(), observed_at=FIXTURE_CLOCK)
    assert result["status"] == "recorded"
    assert result["evidence_admissible"] is True
    assert result["permission_granted"] is False
    assert result["live_restore_performed"] is False
    assert result["committed_sink"]["live_restore_performed"] is False


def test_missing_operator_approval_refusal() -> None:
    request = request_from_fixture(_restore_fixture(operator_ref=None))
    result = validate_checkpoint_restore_request(request, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == REFUSED_MISSING_OPERATOR_APPROVAL


def test_stale_approval_refusal() -> None:
    request = request_from_fixture(_restore_fixture(approval_expires_at=PAST_EXPIRY))
    result = validate_checkpoint_restore_request(request, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == REFUSED_STALE_APPROVAL


def test_missing_iam_refusal() -> None:
    request = request_from_fixture(_restore_fixture(operator_ref="bob"))
    result = validate_checkpoint_restore_request(request, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == REFUSED_MISSING_IAM


def test_missing_tim_freshness_refusal() -> None:
    request = request_from_fixture(_restore_fixture(freshness_ref="tim:missing"))
    result = validate_checkpoint_restore_request(request, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == REFUSED_MISSING_TIM_FRESHNESS


def test_stale_tim_refusal() -> None:
    request = request_from_fixture(_restore_fixture(freshness_ref="tim:stale"))
    result = validate_checkpoint_restore_request(request, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == REFUSED_STALE_TIM


def test_missing_gpp_permit_refusal() -> None:
    request = request_from_fixture(_restore_fixture(requires_gpp=True))
    result = validate_checkpoint_restore_request(request, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == REFUSED_MISSING_GPP_PERMIT


def test_missing_ueak_admission_refusal() -> None:
    request = request_from_fixture(_restore_fixture(requires_ueak=True))
    result = validate_checkpoint_restore_request(request, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == REFUSED_MISSING_UEAK_ADMISSION


def test_revoked_permit_refusal() -> None:
    request = request_from_fixture(_restore_fixture(gpp_permit_ref="gpp:revoked:fixture"))
    result = validate_checkpoint_restore_request(request, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == REFUSED_REVOKED_PERMIT


def test_stale_memory_claim_refusal() -> None:
    request = request_from_fixture(_restore_fixture(stale_memory_ref="memory:stale:truth"))
    result = validate_checkpoint_restore_request(request, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == REFUSED_STALE_MEMORY_CLAIM


def test_identity_overclaim_refusal() -> None:
    request = request_from_fixture(_restore_fixture(continuity_claim_ref="identity:overclaim:fixture"))
    result = validate_checkpoint_restore_request(request, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == REFUSED_IDENTITY_OVERCLAIM


def test_missing_rollback_plan_refusal() -> None:
    request = request_from_fixture(_restore_fixture(rollback_plan_ref=None))
    result = validate_checkpoint_restore_request(request, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == REFUSED_MISSING_ROLLBACK_PLAN


def test_authority_conversion_refusal() -> None:
    bundle = next(b for b in load_reb_restore_fixtures() if b["bundle_id"] == "reb-restore-authority-conversion")
    result = process_reb_restore_bundle(bundle, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "contained"
    assert result["reason_code"] == REFUSED_AUTHORITY_CONVERSION


def test_secret_redaction() -> None:
    with pytest.raises(RebRestoreValidationError):
        request_from_fixture(_restore_fixture(checkpoint_digest="password=secret123"))


def test_deterministic_replay_hash() -> None:
    bundles = list(load_reb_restore_fixtures()[:6])
    _, h1 = replay_fixture_stream(bundles, observed_at=FIXTURE_CLOCK)
    _, h2 = replay_fixture_stream(bundles, observed_at=FIXTURE_CLOCK)
    assert h1 == h2
    assert h1.startswith("sha256:")


def test_continuity_refusal_recorded() -> None:
    bundle = next(b for b in load_reb_restore_fixtures() if b["bundle_id"] == "reb-restore-valid-continuity-refusal")
    result = process_reb_restore_bundle(bundle, observed_at=FIXTURE_CLOCK)
    refusal = result.get("continuity_refusal_result")
    assert isinstance(refusal, dict)
    assert refusal.get("status") == "recorded"
    assert result["permission_granted"] is False


def test_compensation_from_continuity_refusal() -> None:
    bundle = next(b for b in load_reb_restore_fixtures() if b["bundle_id"] == "reb-restore-valid-continuity-refusal")
    result = process_reb_restore_bundle(bundle, observed_at=FIXTURE_CLOCK)
    compensation = result.get("compensation_result")
    assert isinstance(compensation, dict)
    assert compensation.get("status") == "recorded"
    assert result["live_restore_performed"] is False


def test_no_out_of_scope_live_action() -> None:
    bundle = next(b for b in load_reb_restore_fixtures() if b["bundle_id"] == "reb-restore-out-of-scope-live")
    result = process_reb_restore_bundle(bundle, observed_at=FIXTURE_CLOCK)
    assert result["permission_granted"] is False
    assert result["live_action_performed"] is False
    assert result["live_restore_performed"] is False


def test_fake_sink_never_live_restore() -> None:
    candidate = RestoreCandidate(
        candidate_id="reb-cand-sink",
        request_id="reb-req-sink",
        restore_kind="checkpoint",
        checkpoint_digest="digest:sink",
        operator_ref="op:local",
    )
    staged = stage_to_fake_sink(candidate, observed_at=FIXTURE_CLOCK)
    assert staged["live_restore_performed"] is False
    assert staged["sink_type"] == "fake"
    receipt = RestoreReceipt(
        receipt_id="reb-rcpt-sink",
        request_id="reb-req-sink",
        candidate_id="reb-cand-sink",
        restore_kind="checkpoint",
        status="recorded",
        reason_code=REB_RESTORE_CANDIDATE_BOUND,
        operator_ref="op:local",
    )
    committed = commit_to_fake_sink(receipt, observed_at=FIXTURE_CLOCK)
    assert committed["live_restore_performed"] is False
    assert committed["sink_type"] == "fake"


def test_tep_wrapped_candidate() -> None:
    result = process_checkpoint_restore(_restore_fixture(), observed_at=FIXTURE_CLOCK)
    tep = result.get("tep_wrapped")
    assert isinstance(tep, dict)
    candidate = result.get("candidate")
    assert isinstance(candidate, dict)
    assert candidate.get("authority_created") is False
    assert candidate.get("permission_granted") is False


def test_restore_adapter_fixture() -> None:
    adapter = run_reentry_restore_fixture(observed_at=FIXTURE_CLOCK)
    assert adapter["live_restore_performed"] is False
    assert "tep_emission" in adapter


def test_refuse_reb_as_authority_raises() -> None:
    with pytest.raises(ValueError):
        refuse_reb_as_authority(treat_as_authority=True)


def test_analyze_fixtures_all_advisory() -> None:
    analysis = analyze_reb_restore_fixtures(observed_at=FIXTURE_CLOCK)
    assert analysis["all_advisory"] is True
    assert analysis["no_authority_created"] is True
    assert analysis["no_live_restore"] is True


def test_continuity_refusal_helper() -> None:
    receipt = RestoreReceipt(
        receipt_id="reb-rcpt-ref",
        request_id="reb-req-ref",
        candidate_id="reb-cand-ref",
        restore_kind="checkpoint",
        status="recorded",
        reason_code=REB_RESTORE_CANDIDATE_BOUND,
        operator_ref="op:local",
    )
    r = continuity_refusal_record(
        receipt,
        continuity_claim_ref="continuity:refusal:fixture",
        observed_at=FIXTURE_CLOCK,
    )
    assert r["status"] == "recorded"
    assert r["live_restore_performed"] is False
