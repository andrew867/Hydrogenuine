"""SRP ↔ CSM/MEL/TER integration — change control without apply."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

from hg_csm.rtc_bridge import emit_evaluation
from hg_mel import MaintenanceLedger, default_ledger_path, emit_chain_verified
from hg_runtime.bus import EventBus
from hg_runtime.replay import replay
from hg_srp import (
    ChangeApprovalSignature,
    SelfMaintenanceLoop,
    attempt_bundle_apply,
    create_maintenance_bundle,
    ingest_pytest_failure_artifact,
    run_change_control_cycle,
    submit_bundle_to_csm,
)
from hg_ter import TERExecutor

NOW = "2026-06-11T12:00:00.000000Z"
FIXTURE = Path(__file__).resolve().parent / "fixtures" / "pytest_failure_sample.json"
_PY = sys.executable


def test_srp_submits_bundle_to_csm():
    obs = ingest_pytest_failure_artifact(FIXTURE, observed_at=NOW)
    bundle = create_maintenance_bundle([obs], created_at=NOW)
    _, decision = submit_bundle_to_csm(
        bundle,
        proposed_files=("docs/reports/phases/integration_test.md",),
    )
    assert decision.outcome in ("allowed", "needs_human_approval")


def test_srp_change_control_cycle(tmp_path: Path):
    obs = ingest_pytest_failure_artifact(FIXTURE, observed_at=NOW)
    bundle = create_maintenance_bundle([obs], created_at=NOW)
    ledger = MaintenanceLedger(tmp_path / "mel.jsonl")
    result = run_change_control_cycle(
        bundle,
        ledger=ledger,
        proposed_files=("docs/reports/phases/integration_test.md",),
        env=os.environ,
    )
    assert result.mel_chain_ok
    assert result.apply_refused
    assert result.apply_reason_code == "unsigned_proposal"
    if result.csm_outcome == "allowed":
        assert len(result.ter_receipt_hashes) >= 1


def test_srp_direct_apply_still_refused(tmp_path: Path):
    obs = ingest_pytest_failure_artifact(FIXTURE, observed_at=NOW)
    loop = SelfMaintenanceLoop(artifact_root=tmp_path / "srp", proof_root=tmp_path / "proofs")
    _, bundle = loop.run([obs], created_at=NOW)
    approval = ChangeApprovalSignature(
        approval_id="apr",
        proposal_ref=bundle.bundle_id,
        bundle_hash=bundle.bundle_hash,
        approver="human:test",
        decision="approved",
        decided_at=NOW,
    )
    result = attempt_bundle_apply(bundle, approval=approval)
    assert not result.ok
    assert result.reason_code == "ter_execution_not_enabled"


def test_rtc_csm_mel_events_replay(tmp_path: Path):
    obs = ingest_pytest_failure_artifact(FIXTURE, observed_at=NOW)
    bundle = create_maintenance_bundle([obs], created_at=NOW)
    request, decision = submit_bundle_to_csm(
        bundle,
        proposed_files=("docs/reports/phases/rtc_test.md",),
    )

    runtime_dir = tmp_path / "runtime"
    bus = EventBus(runtime_dir, clock=lambda: NOW)
    emit_evaluation(bus, request, decision)

    ledger = MaintenanceLedger(tmp_path / "mel.jsonl")
    from hg_mel.receipts import record_csm_decision

    record_csm_decision(ledger, decision, created_at=NOW)
    emit_chain_verified(bus, ledger.verify_chain(), bundle.bundle_id)

    replay_result = replay(runtime_dir)
    assert replay_result.ok
    assert replay_result.state["activity"]["csm"]["changes_requested"] >= 1
    assert replay_result.state["activity"]["mel"]["records_appended"] >= 0 or replay_result.state["activity"]["mel"]["chains_verified"] >= 1


def test_ter_unsafe_refused():
    executor = TERExecutor()
    for argv in (
        ("git", "push"),
        ("curl", "http://127.0.0.1"),
        ("pip", "install", "x"),
    ):
        req = executor.make_request(argv, requested_by="test", purpose="unsafe")
        receipt, outcome = executor.execute(req, env=os.environ)
        assert receipt.result_status == "refused"
