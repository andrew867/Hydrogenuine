"""SRP Phase 1 proposal-only self-repair tests."""

from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

from jsonschema import validate

from hg_runtime.bus import EventBus
from hg_runtime.replay import replay
from hg_srp import (
    ChangeApprovalSignature,
    RepairProposal,
    SRPPhase1Loop,
    attempt_bundle_apply,
    emit_phase1_cycle,
    observe_from_failing_test,
    verify_human_signature,
)
from hg_srp.artifacts import load_proposal_artifact, repair_proposal_artifact_path

NOW = "2026-06-11T10:00:00.000000Z"
TEST_REF = "tests/fixture/test_broken.py::test_fails"


def _py_file_hashes(root: Path) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for path in root.rglob("*.py"):
        if "srp" in path.parts and "proposals" in path.parts:
            continue
        hashes[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
    return hashes


def test_failing_test_observation_generates_proposal_event(tmp_path: Path):
    bus = EventBus(tmp_path / "runtime", clock=lambda: NOW)
    emit_phase1_cycle(
        bus,
        tmp_path / "srp",
        observed_at=NOW,
        test_ref=TEST_REF,
        runtime_trace_refs=("trace:runtime/tick-42",),
        invariant_violation_refs=("invariant:INV-A33",),
        source_file_refs=("hg_fixture/module.py",),
    )
    events = list(bus.read_all())
    types = [event["type"] for event in events]
    assert types == ["SRP_DRIFT_OBSERVED", "GAP_DETECTED", "SRP_REPAIR_PROPOSED"]

    drift = events[0]["payload"]
    assert drift["failing_test_refs"] == [TEST_REF]
    assert drift["runtime_trace_refs"] == ["trace:runtime/tick-42"]
    assert drift["invariant_violation_refs"] == ["invariant:INV-A33"]
    assert drift["source_file_refs"] == ["hg_fixture/module.py"]

    proposal = events[2]["payload"]
    assert proposal["status"] == "PROPOSED"
    assert proposal["signature_required"] is True
    assert proposal["bundle_hash"].startswith("sha256:")
    assert proposal["target_files"] == ["hg_fixture/module.py"]


def test_repair_proposal_schema_and_bundle_metadata(tmp_path: Path):
    loop = SRPPhase1Loop(tmp_path / "srp")
    drafts = loop.run_from_failing_test(test_ref=TEST_REF, observed_at=NOW, source_file_refs=("src/fix.py",))
    proposal_draft = next(item for item in drafts if item["type"] == "SRP_REPAIR_PROPOSED")
    payload = proposal_draft["payload"]
    validate(
        instance={key: payload[key] for key in payload if key != "artifact_path"},
        schema=json.loads(
            Path("docs/schemas/srp_repair_proposal_v1.json").read_text(encoding="utf-8")
        ),
    )
    assert payload["status"] == "PROPOSED"
    assert payload["signature_required"] is True


def test_proposal_generation_does_not_modify_source_files(tmp_path: Path):
    workspace = tmp_path / "workspace"
    src = workspace / "src"
    src.mkdir(parents=True)
    target = src / "module.py"
    target.write_text("def broken():\n    return 1\n", encoding="utf-8")

    before = _py_file_hashes(workspace)
    loop = SRPPhase1Loop(tmp_path / "srp")
    loop.run_from_failing_test(
        test_ref=TEST_REF,
        observed_at=NOW,
        source_file_refs=(str(target.relative_to(workspace)).replace("\\", "/"),),
    )
    after = _py_file_hashes(workspace)
    assert before == after
    assert target.read_text(encoding="utf-8") == "def broken():\n    return 1\n"


def test_unsigned_repair_proposal_cannot_execute(tmp_path: Path):
    loop = SRPPhase1Loop(tmp_path / "srp")
    proposal_payload = next(
        item for item in loop.run_from_failing_test(test_ref=TEST_REF, observed_at=NOW)
        if item["type"] == "SRP_REPAIR_PROPOSED"
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
    result = attempt_bundle_apply(proposal, approval=None)
    assert result.ok is False
    assert result.reason == "unsigned_proposal"


def test_signed_proposal_still_cannot_apply_without_ter(tmp_path: Path):
    loop = SRPPhase1Loop(tmp_path / "srp")
    proposal_payload = next(
        item for item in loop.run_from_failing_test(test_ref=TEST_REF, observed_at=NOW)
        if item["type"] == "SRP_REPAIR_PROPOSED"
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
        approval_id="apr_phase1",
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


def test_replay_preserves_proposal_state(tmp_path: Path):
    bus = EventBus(tmp_path / "runtime", clock=lambda: NOW)
    emit_phase1_cycle(bus, tmp_path / "srp", observed_at=NOW, test_ref=TEST_REF)
    events = list(bus.read_all())
    proposal = next(event for event in events if event["type"] == "SRP_REPAIR_PROPOSED")
    artifact = load_proposal_artifact(Path(proposal["payload"]["artifact_path"]))
    assert artifact["bundle_hash"] == proposal["payload"]["bundle_hash"]
    assert repair_proposal_artifact_path(tmp_path / "srp", artifact["proposal_id"]).exists()

    result = replay(tmp_path / "runtime")
    assert result.ok is True
    assert result.state["activity"]["srp"]["drifts_observed"] == 1
    assert result.state["activity"]["srp"]["proposals"] == 1
    pending = result.state["goals"]["pending_tasks"]
    assert pending[-1]["status"] == "PROPOSED"
    assert pending[-1]["signature_required"] is True


def test_observe_from_failing_test_drift_model():
    drift = observe_from_failing_test(test_ref=TEST_REF, observed_at=NOW)
    assert drift.kind == "failing_test"
    assert drift.failing_test_refs == (TEST_REF,)


def test_srp_phase1_has_no_direct_execution_imports():
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
