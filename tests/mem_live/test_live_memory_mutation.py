"""MEM-LIVE governed live memory mutation tests."""

from __future__ import annotations

import pytest

from hg_core.iam.registry import clear_registry_cache, load_registry
from hg_core.iam.types import reset_iam_event_ledger
from hg_core.mem_live.errors import (
    MEM_WRITE_CANDIDATE_BOUND,
    REFUSED_AUTHORITY_CONVERSION,
    REFUSED_MISSING_GPP_PERMIT,
    REFUSED_MISSING_IAM,
    REFUSED_MISSING_OPERATOR_APPROVAL,
    REFUSED_MISSING_TIM_FRESHNESS,
    REFUSED_MISSING_UEAK_ADMISSION,
    REFUSED_STALE_APPROVAL,
    REFUSED_STALE_TIM,
    MemValidationError,
)
from hg_runtime.live_memory_mutation import (
    FIXTURE_CLOCK,
    FUTURE_EXPIRY,
    PAST_EXPIRY,
    analyze_mem_fixtures,
    commit_to_fake_sink,
    load_mem_fixtures,
    process_mem_bundle,
    process_memory_mutation,
    refuse_mem_as_authority,
    replay_fixture_stream,
    request_from_fixture,
    request_to_fake_sink,
    restore_from_rollback,
    rollback_memory_mutation,
    run_memory_mutation_fixture,
    validate_memory_mutation_request,
)
from hg_runtime.live_memory_mutation.types import MemoryMutationReceipt, MemoryWriteCandidate


@pytest.fixture(autouse=True)
def _reset_iam() -> None:
    clear_registry_cache()
    reset_iam_event_ledger()
    load_registry()


def _write_fixture(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "request_id": "mem-test-write",
        "mutation_kind": "write",
        "memory_key": "mem:session:test",
        "payload_digest": "digest:test",
        "operator_ref": "op:local",
        "freshness_ref": "tim:approval_window_ok",
        "approval_expires_at": FUTURE_EXPIRY,
        "scope": "approve_change",
        "rollback_plan_ref": "rollback:plan:test",
        "observed_at": FIXTURE_CLOCK,
    }
    base.update(overrides)
    return base


def test_valid_write_fixture_path() -> None:
    result = process_memory_mutation(_write_fixture(), observed_at=FIXTURE_CLOCK)
    assert result["status"] == "recorded"
    assert result["evidence_admissible"] is True
    assert result["permission_granted"] is False
    assert result["durable_write_performed"] is False
    assert result["committed_sink"]["durable_write_performed"] is False


def test_missing_operator_approval_refusal() -> None:
    request = request_from_fixture(_write_fixture(operator_ref=None))
    result = validate_memory_mutation_request(request, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == REFUSED_MISSING_OPERATOR_APPROVAL


def test_stale_approval_refusal() -> None:
    request = request_from_fixture(_write_fixture(approval_expires_at=PAST_EXPIRY))
    result = validate_memory_mutation_request(request, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == REFUSED_STALE_APPROVAL


def test_missing_iam_refusal() -> None:
    request = request_from_fixture(_write_fixture(operator_ref="bob"))
    result = validate_memory_mutation_request(request, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == REFUSED_MISSING_IAM


def test_missing_tim_freshness_refusal() -> None:
    request = request_from_fixture(_write_fixture(freshness_ref="tim:missing"))
    result = validate_memory_mutation_request(request, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == REFUSED_MISSING_TIM_FRESHNESS


def test_stale_tim_refusal() -> None:
    request = request_from_fixture(_write_fixture(freshness_ref="tim:stale"))
    result = validate_memory_mutation_request(request, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == REFUSED_STALE_TIM


def test_missing_gpp_permit_refusal() -> None:
    request = request_from_fixture(_write_fixture(requires_gpp=True))
    result = validate_memory_mutation_request(request, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == REFUSED_MISSING_GPP_PERMIT


def test_missing_ueak_admission_refusal() -> None:
    request = request_from_fixture(_write_fixture(requires_ueak=True))
    result = validate_memory_mutation_request(request, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == REFUSED_MISSING_UEAK_ADMISSION


def test_authority_conversion_refusal() -> None:
    bundle = next(b for b in load_mem_fixtures() if b["bundle_id"] == "mem-authority-conversion")
    result = process_mem_bundle(bundle, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "contained"
    assert result["reason_code"] == REFUSED_AUTHORITY_CONVERSION


def test_secret_redaction() -> None:
    with pytest.raises(MemValidationError):
        request_from_fixture(_write_fixture(memory_key="password=secret123"))


def test_deterministic_replay_hash() -> None:
    bundles = list(load_mem_fixtures()[:6])
    _, h1 = replay_fixture_stream(bundles, observed_at=FIXTURE_CLOCK)
    _, h2 = replay_fixture_stream(bundles, observed_at=FIXTURE_CLOCK)
    assert h1 == h2
    assert h1.startswith("sha256:")


def test_rollback_recorded() -> None:
    bundle = next(b for b in load_mem_fixtures() if b["bundle_id"] == "mem-valid-rollback")
    result = process_mem_bundle(bundle, observed_at=FIXTURE_CLOCK)
    rollback = result.get("rollback_result")
    assert isinstance(rollback, dict)
    assert rollback.get("rollback_acknowledged") is True
    assert result["permission_granted"] is False


def test_restore_from_rollback() -> None:
    bundle = next(b for b in load_mem_fixtures() if b["bundle_id"] == "mem-valid-restore")
    result = process_mem_bundle(bundle, observed_at=FIXTURE_CLOCK)
    restore = result.get("restore_result")
    assert isinstance(restore, dict)
    assert restore.get("restore_available") is True
    assert result["durable_write_performed"] is False


def test_no_out_of_scope_live_action() -> None:
    bundle = next(b for b in load_mem_fixtures() if b["bundle_id"] == "mem-out-of-scope-live")
    result = process_mem_bundle(bundle, observed_at=FIXTURE_CLOCK)
    assert result["permission_granted"] is False
    assert result["live_action_performed"] is False
    assert result["durable_write_performed"] is False


def test_fake_sink_never_durable() -> None:
    candidate = MemoryWriteCandidate(
        candidate_id="mem-cand-sink",
        request_id="mem-req-sink",
        mutation_kind="write",
        memory_key="mem:session:sink",
        payload_digest="digest:sink",
        operator_ref="op:local",
    )
    staged = request_to_fake_sink(candidate, observed_at=FIXTURE_CLOCK)
    assert staged["durable_write_performed"] is False
    assert staged["sink_type"] == "fake"
    receipt = MemoryMutationReceipt(
        receipt_id="mem-rcpt-sink",
        request_id="mem-req-sink",
        candidate_id="mem-cand-sink",
        mutation_kind="write",
        status="recorded",
        reason_code=MEM_WRITE_CANDIDATE_BOUND,
        operator_ref="op:local",
    )
    committed = commit_to_fake_sink(receipt, observed_at=FIXTURE_CLOCK)
    assert committed["durable_write_performed"] is False
    assert committed["sink_type"] == "fake"


def test_tep_wrapped_candidate() -> None:
    result = process_memory_mutation(_write_fixture(), observed_at=FIXTURE_CLOCK)
    tep = result.get("tep_wrapped")
    assert isinstance(tep, dict)
    candidate = result.get("candidate")
    assert isinstance(candidate, dict)
    assert candidate.get("authority_created") is False
    assert candidate.get("permission_granted") is False


def test_mutation_adapter_fixture() -> None:
    adapter = run_memory_mutation_fixture(observed_at=FIXTURE_CLOCK)
    assert adapter["durable_write_performed"] is False
    assert "tep_emission" in adapter


def test_refuse_mem_as_authority_raises() -> None:
    with pytest.raises(ValueError):
        refuse_mem_as_authority(treat_as_authority=True)


def test_analyze_fixtures_all_advisory() -> None:
    analysis = analyze_mem_fixtures(observed_at=FIXTURE_CLOCK)
    assert analysis["all_advisory"] is True
    assert analysis["no_authority_created"] is True
    assert analysis["no_durable_writes"] is True


def test_rollback_helper() -> None:
    receipt = MemoryMutationReceipt(
        receipt_id="mem-rcpt-rbk",
        request_id="mem-req-rbk",
        candidate_id="mem-cand-rbk",
        mutation_kind="write",
        status="recorded",
        reason_code=MEM_WRITE_CANDIDATE_BOUND,
        operator_ref="op:local",
    )
    rb = rollback_memory_mutation(
        receipt,
        memory_key="mem:session:rbk",
        prior_digest="digest:prior",
        observed_at=FIXTURE_CLOCK,
    )
    assert rb["rollback_acknowledged"] is True
    assert rb["durable_write_performed"] is False


def test_restore_helper() -> None:
    rb = restore_from_rollback(
        {"rollback_id": "mem-rbk-test", "memory_key": "mem:session:rst"},
        restored_digest="digest:restored",
        observed_at=FIXTURE_CLOCK,
    )
    assert rb["restore_available"] is True
    assert rb["durable_write_performed"] is False
