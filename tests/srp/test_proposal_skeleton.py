from __future__ import annotations

import ast
import json
from pathlib import Path

from jsonschema import validate

from hg_runtime.bus import EventBus
from hg_runtime.replay import replay
from hg_srp import (
    ChangeApprovalSignature,
    RepairProposal,
    SRPSkeletonLoop,
    attempt_bundle_apply,
    emit_skeleton_cycle,
    verify_human_signature,
)
from hg_srp.artifacts import load_proposal_artifact, repair_proposal_artifact_path


NOW = "2026-06-11T08:00:00.000000Z"


def test_repair_proposal_has_exact_bundle_hash(tmp_path: Path):
    loop = SRPSkeletonLoop(tmp_path / "srp")
    drafts = loop.run_once(observed_at=NOW, subject="fixture/module_a.py")
    proposal = next(item for item in drafts if item["type"] == "SRP_REPAIR_PROPOSED")
    payload = proposal["payload"]
    assert payload["bundle_hash"].startswith("sha256:")
    assert payload["status"] == "PROPOSED"
    validate(
        instance={key: payload[key] for key in payload if key != "artifact_path"},
        schema=json.loads(
            Path("docs/schemas/srp_repair_proposal_v1.json").read_text(encoding="utf-8")
        ),
    )


def test_unsigned_proposal_apply_is_rejected(tmp_path: Path):
    payload = SRPSkeletonLoop(tmp_path / "srp").run_once(observed_at=NOW)[-1]["payload"]
    proposal = RepairProposal(
        proposal_id=payload["proposal_id"],
        drift_ref=payload["drift_ref"],
        gap_ref=payload["gap_ref"],
        target_files=tuple(payload["target_files"]),
        intended_change_summary=payload["intended_change_summary"],
        test_plan=payload["test_plan"],
        risk_notes=payload["risk_notes"],
        created_at=payload["created_at"],
    )
    result = attempt_bundle_apply(proposal, approval=None)
    assert result.ok is False
    assert result.reason == "unsigned_proposal"


def test_mismatched_signature_is_rejected(tmp_path: Path):
    loop = SRPSkeletonLoop(tmp_path / "srp")
    proposal_payload = next(
        item for item in loop.run_once(observed_at=NOW) if item["type"] == "SRP_REPAIR_PROPOSED"
    )["payload"]
    proposal = RepairProposal(
        proposal_id=proposal_payload["proposal_id"],
        drift_ref=proposal_payload["drift_ref"],
        gap_ref=proposal_payload["gap_ref"],
        target_files=tuple(proposal_payload["target_files"]),
        intended_change_summary=proposal_payload["intended_change_summary"],
        test_plan=proposal_payload["test_plan"],
        risk_notes=proposal_payload["risk_notes"],
        created_at=proposal_payload["created_at"],
    )
    approval = ChangeApprovalSignature(
        approval_id="apr_test",
        proposal_ref=proposal.proposal_id,
        bundle_hash="sha256:" + "0" * 64,
        approver="human:operator",
        decision="approved",
        decided_at=NOW,
    )
    assert verify_human_signature(approval, expected_bundle_hash=proposal.bundle_hash) is False
    result = attempt_bundle_apply(proposal, approval=approval)
    assert result.ok is False
    assert result.reason == "signature_or_hash_mismatch"


def test_signed_proposal_still_cannot_apply_without_ter(tmp_path: Path):
    loop = SRPSkeletonLoop(tmp_path / "srp")
    proposal_payload = next(
        item for item in loop.run_once(observed_at=NOW) if item["type"] == "SRP_REPAIR_PROPOSED"
    )["payload"]
    proposal = RepairProposal(
        proposal_id=proposal_payload["proposal_id"],
        drift_ref=proposal_payload["drift_ref"],
        gap_ref=proposal_payload["gap_ref"],
        target_files=tuple(proposal_payload["target_files"]),
        intended_change_summary=proposal_payload["intended_change_summary"],
        test_plan=proposal_payload["test_plan"],
        risk_notes=proposal_payload["risk_notes"],
        created_at=proposal_payload["created_at"],
    )
    approval = ChangeApprovalSignature(
        approval_id="apr_test",
        proposal_ref=proposal.proposal_id,
        bundle_hash=proposal.bundle_hash,
        approver="human:operator",
        decision="approved",
        decided_at=NOW,
    )
    assert verify_human_signature(approval, expected_bundle_hash=proposal.bundle_hash) is True
    result = attempt_bundle_apply(proposal, approval=approval)
    assert result.ok is False
    assert result.reason_code == "ter_execution_not_enabled"


def test_proposal_artifacts_and_events_are_traceable(tmp_path: Path):
    bus = EventBus(tmp_path / "runtime", clock=lambda: NOW)
    emit_skeleton_cycle(bus, tmp_path / "srp", observed_at=NOW)
    events = list(bus.read_all())
    types = [event["type"] for event in events]
    assert types == ["SRP_DRIFT_OBSERVED", "GAP_DETECTED", "SRP_REPAIR_PROPOSED"]
    assert list(events[1]["causal_parents"]) == [events[0]["event_id"]]
    assert list(events[2]["causal_parents"]) == [events[1]["event_id"]]
    proposal = [event for event in events if event["type"] == "SRP_REPAIR_PROPOSED"][-1]
    artifact = load_proposal_artifact(Path(proposal["payload"]["artifact_path"]))
    assert artifact["bundle_hash"] == proposal["payload"]["bundle_hash"]
    assert repair_proposal_artifact_path(tmp_path / "srp", artifact["proposal_id"]).exists()
    result = replay(tmp_path / "runtime")
    assert result.ok is True
    assert result.state["activity"]["srp"]["drifts_observed"] == 1
    assert result.state["activity"]["srp"]["proposals"] == 1


def test_srp_skeleton_has_no_direct_execution_imports():
    forbidden_prefixes = (
        "subprocess",
        "git",
        "hg_ueak",
        "hg_oea",
        "shutil",
        "socket",
        "httpx",
        "requests",
    )
    apply_phase_modules = {
        "apply_workflow.py",
        "sandbox.py",
        "patch_apply.py",
        "self_edit_workflow.py",
        "self_edit_verification.py",
    }
    for path in Path("hg_srp").glob("*.py"):
        if path.name in apply_phase_modules:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imports: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module)
        for name in imports:
            assert not any(name == prefix or name.startswith(prefix + ".") for prefix in forbidden_prefixes)
