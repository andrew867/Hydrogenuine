"""SRP self-maintenance integration tests."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from jsonschema import validate

from hg_crr import Phase1RecoveryHandler
from hg_runtime.bus import EventBus
from hg_runtime.handlers import (
    StubArousalReader,
    StubCognitionHandler,
    StubDecisionHandler,
    StubKernelHandler,
    StubMemoryHandler,
)
from hg_runtime.loop import RuntimeLoop
from hg_runtime.replay import replay
from hg_srp import (
    ChangeApprovalSignature,
    SelfMaintenanceLoop,
    attempt_bundle_apply,
    attempt_handoff,
    create_maintenance_bundle,
    emit_maintenance_cycle,
    ingest_audit_finding_artifact,
    ingest_pytest_failure_artifact,
    maintenance_memory_receipt,
    verify_bundle_unchanged,
    verify_human_signature,
)

NOW = "2026-06-11T12:00:00.000000Z"
FIXTURES = Path(__file__).parent / "fixtures"


def _clock():
    return NOW


def test_pytest_artifact_intake_is_deterministic():
    obs1 = ingest_pytest_failure_artifact(FIXTURES / "pytest_failure_sample.json", observed_at=NOW)
    obs2 = ingest_pytest_failure_artifact(FIXTURES / "pytest_failure_sample.json", observed_at=NOW)
    assert obs1.observation_hash == obs2.observation_hash
    assert obs1.source_kind == "failing_test"


def test_audit_finding_intake():
    obs = ingest_audit_finding_artifact(FIXTURES / "audit_finding_sample.json", observed_at=NOW)
    assert obs.source_kind == "audit_finding"
    assert obs.observation_class == "architecture_drift"
    assert "HYDROGENUINE" in obs.summary


def test_bundle_hash_changes_with_content():
    obs = ingest_pytest_failure_artifact(FIXTURES / "pytest_failure_sample.json", observed_at=NOW)
    b1 = create_maintenance_bundle([obs], created_at=NOW)
    obs2 = ingest_audit_finding_artifact(FIXTURES / "audit_finding_sample.json", observed_at=NOW)
    b2 = create_maintenance_bundle([obs, obs2], created_at=NOW)
    assert b1.bundle_hash != b2.bundle_hash


def test_maintenance_cycle_emits_rtc_events(tmp_path: Path):
    obs = ingest_pytest_failure_artifact(FIXTURES / "pytest_failure_sample.json", observed_at=NOW)
    bus = EventBus(tmp_path / "runtime", clock=_clock)
    emit_maintenance_cycle(bus, tmp_path / "srp", [obs], observed_at=NOW, proof_root=tmp_path / "proofs")
    types = [e["type"] for e in bus.read_all()]
    assert "SRP_TEST_FAILURE_OBSERVED" in types
    assert "SRP_PROPOSAL_BUNDLE_CREATED" in types
    assert "SRP_PROPOSAL_BUNDLE_HASHED" in types
    assert "SRP_HUMAN_SIGNATURE_REQUIRED" in types
    assert "SRP_APPLY_REFUSED" in types
    assert "SRP_MAINTENANCE_OUTCOME_RECORDED" in types


def test_unsigned_apply_and_handoff_refused(tmp_path: Path):
    obs = ingest_pytest_failure_artifact(FIXTURES / "pytest_failure_sample.json", observed_at=NOW)
    loop = SelfMaintenanceLoop(artifact_root=tmp_path / "srp", proof_root=tmp_path / "proofs")
    _drafts, bundle = loop.run([obs], created_at=NOW)
    apply = attempt_bundle_apply(bundle, approval=None)
    assert apply.ok is False
    assert apply.reason_code == "unsigned_proposal"
    handoff = attempt_handoff(bundle, None, proof_root=tmp_path / "proofs")
    assert handoff.ok is False
    assert handoff.reason_code == "unsigned_proposal"


def test_signature_binds_exact_bundle_hash(tmp_path: Path):
    obs = ingest_pytest_failure_artifact(FIXTURES / "pytest_failure_sample.json", observed_at=NOW)
    bundle = create_maintenance_bundle([obs], created_at=NOW)
    approval = ChangeApprovalSignature(
        approval_id="apr1",
        proposal_ref=bundle.bundle_id,
        bundle_hash=bundle.bundle_hash,
        approver="human:operator",
        decision="approved",
        decided_at=NOW,
    )
    assert verify_human_signature(approval, expected_bundle_hash=bundle.bundle_hash) is True
    assert verify_bundle_unchanged(bundle, approval) is True


def test_modified_bundle_after_signature_refused(tmp_path: Path):
    obs = ingest_pytest_failure_artifact(FIXTURES / "pytest_failure_sample.json", observed_at=NOW)
    bundle = create_maintenance_bundle([obs], created_at=NOW)
    approval = ChangeApprovalSignature(
        approval_id="apr1",
        proposal_ref=bundle.bundle_id,
        bundle_hash=bundle.bundle_hash,
        approver="human:operator",
        decision="approved",
        decided_at=NOW,
    )
    obs2 = ingest_audit_finding_artifact(FIXTURES / "audit_finding_sample.json", observed_at=NOW)
    modified = create_maintenance_bundle([obs, obs2], created_at=NOW, bundle_id=bundle.bundle_id)
    assert modified.bundle_hash != bundle.bundle_hash
    assert verify_human_signature(approval, expected_bundle_hash=modified.bundle_hash) is False


def test_signed_apply_still_refused(tmp_path: Path):
    obs = ingest_pytest_failure_artifact(FIXTURES / "pytest_failure_sample.json", observed_at=NOW)
    bundle = create_maintenance_bundle([obs], created_at=NOW)
    approval = ChangeApprovalSignature(
        approval_id="apr1",
        proposal_ref=bundle.bundle_id,
        bundle_hash=bundle.bundle_hash,
        approver="human:operator",
        decision="approved",
        decided_at=NOW,
    )
    result = attempt_bundle_apply(bundle, approval=approval)
    assert result.ok is False
    assert result.reason_code == "ter_execution_not_enabled"


def test_handoff_artifact_created_without_secrets(tmp_path: Path):
    obs = ingest_pytest_failure_artifact(FIXTURES / "pytest_failure_sample.json", observed_at=NOW)
    loop = SelfMaintenanceLoop(artifact_root=tmp_path / "srp", proof_root=tmp_path / "proofs")
    approval = ChangeApprovalSignature(
        approval_id="apr1",
        proposal_ref="pending",
        bundle_hash="sha256:" + "0" * 64,
        approver="human:operator",
        decision="approved",
        decided_at=NOW,
    )
    _drafts, bundle = loop.run([obs], created_at=NOW)
    approval = ChangeApprovalSignature(
        approval_id="apr1",
        proposal_ref=bundle.bundle_id,
        bundle_hash=bundle.bundle_hash,
        approver="human:operator",
        decision="approved",
        decided_at=NOW,
    )
    bus = EventBus(tmp_path / "runtime", clock=_clock)
    emit_maintenance_cycle(
        bus,
        tmp_path / "srp",
        [obs],
        observed_at=NOW,
        proof_root=tmp_path / "proofs",
        approval=approval,
        create_handoff=True,
    )
    handoff_events = [e for e in bus.read_all() if e["type"] == "SRP_EXTERNAL_TOOL_HANDOFF_CREATED"]
    assert len(handoff_events) == 1
    json_path = Path(handoff_events[0]["payload"]["handoff_json_path"])
    content = json_path.read_text(encoding="utf-8")
    assert "api_key" not in content.lower()
    assert "secret" not in content.lower()
    assert json.loads(content)["no_auto_apply"] is True


def test_proposal_generation_does_not_modify_source(tmp_path: Path):
    workspace = tmp_path / "workspace"
    src = workspace / "src"
    src.mkdir(parents=True)
    target = src / "module.py"
    target.write_text("x = 1\n", encoding="utf-8")
    before = hashlib.sha256(target.read_bytes()).hexdigest()
    obs = ingest_pytest_failure_artifact(FIXTURES / "pytest_failure_sample.json", observed_at=NOW)
    SelfMaintenanceLoop(artifact_root=tmp_path / "srp").run([obs], created_at=NOW)
    after = hashlib.sha256(target.read_bytes()).hexdigest()
    assert before == after


def test_world_state_and_replay(tmp_path: Path):
    obs = ingest_pytest_failure_artifact(FIXTURES / "pytest_failure_sample.json", observed_at=NOW)
    bus = EventBus(tmp_path / "runtime", clock=_clock)
    emit_maintenance_cycle(bus, tmp_path / "srp", [obs], observed_at=NOW, proof_root=tmp_path / "proofs")
    result = replay(tmp_path / "runtime")
    assert result.ok is True
    srp = result.state["activity"]["srp"]
    assert srp["test_failures_observed"] == 1
    assert srp["bundles_created"] == 1
    assert srp["signatures_required"] == 1
    assert srp["apply_refusals"] == 1
    assert srp["outcomes_recorded"] == 1


def test_memory_receipt_is_not_authority(tmp_path: Path):
    obs = ingest_pytest_failure_artifact(FIXTURES / "pytest_failure_sample.json", observed_at=NOW)
    bundle = create_maintenance_bundle([obs], created_at=NOW)
    receipt = maintenance_memory_receipt(bundle, artifact_path=str(tmp_path / "bundle.json"))
    assert receipt["authority"] is False
    assert receipt["signature_required"] is True


def test_crr_recovery_does_not_resolve_proposals(tmp_path: Path):
    recovery = Phase1RecoveryHandler(
        tmp_path / "checkpoints",
        level="L2",
        requested=True,
        manual=True,
        workspace_root=tmp_path,
    )
    loop = RuntimeLoop(
        EventBus(tmp_path / "runtime", clock=_clock),
        cognition=StubCognitionHandler(),
        decision=StubDecisionHandler(),
        kernel=StubKernelHandler(),
        memory=StubMemoryHandler(),
        arousal=StubArousalReader(),
        recovery=recovery,
        runtime_dir=tmp_path / "runtime",
        idle_block_s=0.0,
        snapshot_every_ticks=0,
        require_enabled=False,
    )
    pending = [{"task_id": "srp-proposal", "status": "PROPOSED", "bundle_hash": "sha256:abc"}]
    loop.state["goals"]["pending_tasks"] = list(pending)
    loop.bus.submit("TIMER_EVENT", {"timer_id": "crr"}, source="timer")
    loop.run_once(poll_timeout=0.0)
    assert loop.state["goals"]["pending_tasks"] == pending


def test_maintenance_bundle_schema(tmp_path: Path):
    obs = ingest_pytest_failure_artifact(FIXTURES / "pytest_failure_sample.json", observed_at=NOW)
    bundle = create_maintenance_bundle([obs], created_at=NOW)
    validate(
        instance=bundle.to_payload(),
        schema=json.loads(
            Path("docs/schemas/srp_maintenance_bundle_v1.json").read_text(encoding="utf-8")
        ),
    )


def test_streaming_cognition_has_no_tool_handles():
    from hg_runtime.cognition import StreamingCognitionHandler
    from hg_runtime.cognition.fake_provider import FakeModelProvider

    handler = StreamingCognitionHandler(provider=FakeModelProvider())
    assert not hasattr(handler, "tools")
    assert not hasattr(handler, "tool_handles")


def test_srp_events_registered():
    from hg_runtime.bus import TypeRegistry

    registry = TypeRegistry()
    for name in (
        "SRP_TEST_FAILURE_OBSERVED",
        "SRP_PROPOSAL_BUNDLE_CREATED",
        "SRP_HUMAN_SIGNATURE_REQUIRED",
        "SRP_APPLY_REFUSED",
        "SRP_EXTERNAL_TOOL_HANDOFF_CREATED",
    ):
        assert name in registry
