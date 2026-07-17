"""SRP approval/review apply gate tests — sandbox-only, no autonomous merge."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from hg_runtime.bus import EventBus
from hg_runtime.replay import replay
from hg_srp import (
    ApprovedPatchBundle,
    ChangeApprovalSignature,
    attempt_bundle_apply,
    attempt_merge_to_protected_branch,
    create_maintenance_bundle,
    ingest_pytest_failure_artifact,
    run_approval_review_apply,
    validate_apply_transition,
)
from hg_srp.apply_rtc_bridge import emit_apply_workflow
from hg_srp.apply_lifecycle import (
    STATE_APPLY_REJECTED,
    STATE_APPLY_REQUESTED,
    STATE_MERGE_READY,
    STATE_PATCH_APPLIED_TO_SANDBOX,
    STATE_PROPOSED,
    STATE_SIGNED,
    STATE_TESTS_FAILED,
)
from hg_srp.sandbox import cleanup_sandbox, protected_head_hash, verify_protected_unchanged
from hg_ter import TERExecutor
from hg_ter.types import CommandRequest

NOW = "2026-06-11T14:00:00.000000Z"
FIXTURES = Path(__file__).parent / "fixtures"
SAFE_TEST = Path(__file__).parents[1] / "ter" / "test_safe_fixture.py"


def _init_git_repo(repo: Path) -> None:
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "srp@test"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "srp-test"], cwd=repo, check=True)
    (repo / "tests" / "ter").mkdir(parents=True, exist_ok=True)
    shutil.copy(SAFE_TEST, repo / "tests" / "ter" / "test_safe_fixture.py")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=repo, check=True, capture_output=True)


def _bundle_and_approval(tmp_path: Path):
    obs = ingest_pytest_failure_artifact(FIXTURES / "pytest_failure_sample.json", observed_at=NOW)
    bundle = create_maintenance_bundle([obs], created_at=NOW)
    approval = ChangeApprovalSignature(
        approval_id="apr-apply-1",
        proposal_ref=bundle.bundle_id,
        bundle_hash=bundle.bundle_hash,
        approver="human:operator",
        decision="approved",
        decided_at=NOW,
    )
    patch = ApprovedPatchBundle(
        patch_id="patch-1",
        bundle_ref=bundle.bundle_id,
        bundle_hash=bundle.bundle_hash,
        format="file_overlay",
        file_overlays=(("docs/srp_sandbox_marker.txt", "# harmless sandbox marker\n"),),
        test_commands=("tests/ter/test_safe_fixture.py",),
    )
    return bundle, approval, patch


def test_illegal_lifecycle_transitions():
    assert validate_apply_transition(STATE_SIGNED, "MERGED").ok is False
    assert validate_apply_transition(STATE_PROPOSED, STATE_PATCH_APPLIED_TO_SANDBOX).ok is False
    assert validate_apply_transition(STATE_TESTS_FAILED, STATE_MERGE_READY).ok is False
    assert validate_apply_transition(STATE_APPLY_REQUESTED, STATE_MERGE_READY).ok is False


def test_unsigned_bundle_cannot_apply_sandbox(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_git_repo(repo)
    bundle, _approval, patch = _bundle_and_approval(tmp_path)
    result = run_approval_review_apply(
        bundle,
        None,  # type: ignore[arg-type]
        patch,
        repo_root=repo,
        proof_root=tmp_path / "proofs",
    )
    assert result.ok is False
    assert result.reason_code == "unsigned_proposal"


def test_modified_bundle_after_signature_rejected(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_git_repo(repo)
    bundle, approval, patch = _bundle_and_approval(tmp_path)
    tampered = ApprovedPatchBundle(
        patch_id=patch.patch_id,
        bundle_ref=patch.bundle_ref,
        bundle_hash="sha256:" + "f" * 64,
        format="file_overlay",
        file_overlays=patch.file_overlays,
        test_commands=patch.test_commands,
    )
    result = run_approval_review_apply(
        bundle, approval, tampered, repo_root=repo, proof_root=tmp_path / "proofs"
    )
    assert result.ok is False
    assert result.reason_code == "patch_bundle_mismatch"


def test_wrong_signer_hash_rejected(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_git_repo(repo)
    bundle, approval, patch = _bundle_and_approval(tmp_path)
    bad = ChangeApprovalSignature(
        approval_id=approval.approval_id,
        proposal_ref=approval.proposal_ref,
        bundle_hash=approval.bundle_hash,
        approver="",
        decision="approved",
        decided_at=NOW,
    )
    result = run_approval_review_apply(bundle, bad, patch, repo_root=repo, proof_root=tmp_path / "proofs")
    assert result.ok is False
    assert result.reason_code == "signer_missing"


def test_approved_bundle_applies_only_to_sandbox(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_git_repo(repo)
    head_before = protected_head_hash(repo)
    bundle, approval, patch = _bundle_and_approval(tmp_path)
    result = run_approval_review_apply(
        bundle, approval, patch, repo_root=repo, proof_root=tmp_path / "proofs"
    )
    assert result.ok is True
    assert result.merge_ready is True
    assert result.sandbox_path is not None
    marker = Path(result.sandbox_path) / "docs" / "srp_sandbox_marker.txt"
    assert marker.exists()
    assert not (repo / "docs" / "srp_sandbox_marker.txt").exists()
    assert verify_protected_unchanged(repo, head_before or "")


def test_patch_hash_and_applied_files_recorded(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_git_repo(repo)
    bundle, approval, patch = _bundle_and_approval(tmp_path)
    result = run_approval_review_apply(
        bundle, approval, patch, repo_root=repo, proof_root=tmp_path / "proofs"
    )
    assert result.patch_hash == patch.patch_hash
    assert "docs/srp_sandbox_marker.txt" in result.applied_files


def test_test_failure_blocks_merge_ready(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_git_repo(repo)
    bundle, approval, _patch = _bundle_and_approval(tmp_path)
    patch = ApprovedPatchBundle(
        patch_id="patch-fail",
        bundle_ref=bundle.bundle_id,
        bundle_hash=bundle.bundle_hash,
        format="file_overlay",
        file_overlays=(("tests/ter/test_will_fail.py", "def test_x():\n    assert False\n"),),
        test_commands=("tests/ter/test_will_fail.py",),
    )
    result = run_approval_review_apply(
        bundle,
        approval,
        patch,
        repo_root=repo,
        proof_root=tmp_path / "proofs",
        cleanup_on_failure=True,
    )
    assert result.ok is False
    assert result.reason_code == "tests_failed"
    assert result.merge_ready is False


def test_success_creates_review_artifact(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_git_repo(repo)
    bundle, approval, patch = _bundle_and_approval(tmp_path)
    result = run_approval_review_apply(
        bundle, approval, patch, repo_root=repo, proof_root=tmp_path / "proofs"
    )
    assert result.review_artifact_path is not None
    artifact = json.loads(Path(result.review_artifact_path).read_text(encoding="utf-8"))
    assert artifact["merge_ready"] is True
    assert artifact["final_human_confirmation_required"] is True
    assert artifact["autonomous_merge_enabled"] is False


def test_final_human_confirmation_required_no_auto_merge(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_git_repo(repo)
    bundle, approval, patch = _bundle_and_approval(tmp_path)
    result = run_approval_review_apply(
        bundle, approval, patch, repo_root=repo, proof_root=tmp_path / "proofs"
    )
    merge = attempt_merge_to_protected_branch(
        bundle_hash=result.bundle_hash,
        review_artifact_hash="sha256:abc",
        confirmation_token="token",
    )
    assert merge["ok"] is False
    assert merge["reason_code"] == "autonomous_merge_disabled"


def test_direct_protected_apply_still_refused():
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
    direct = attempt_bundle_apply(bundle, approval=approval)
    assert direct.ok is False
    assert direct.reason_code == "ter_execution_not_enabled"


def test_ter_blocks_unsafe_commands():
    executor = TERExecutor()
    request = CommandRequest(
        request_id="unsafe-1",
        argv=("curl", "https://example.com"),
        cwd=str(Path.cwd()),
        requested_by="test",
        purpose="unsafe",
        created_at=NOW,
    )
    decision = executor.evaluate(request)
    assert decision.allowed is False


def test_rtc_events_emitted_and_replayable(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_git_repo(repo)
    bundle, approval, patch = _bundle_and_approval(tmp_path)
    result = run_approval_review_apply(
        bundle, approval, patch, repo_root=repo, proof_root=tmp_path / "proofs"
    )
    bus = EventBus(tmp_path / "runtime", clock=lambda: NOW)
    emit_apply_workflow(bus, result)
    types = [e["type"] for e in bus.read_all()]
    assert "SRP_APPLY_REQUESTED" in types
    assert "SRP_APPROVAL_VERIFIED" in types
    assert "SRP_APPLY_SANDBOX_PREPARED" in types
    assert "SRP_PATCH_APPLIED" in types
    assert "SRP_APPLY_TESTS_PASSED" in types
    assert "SRP_REVIEW_ARTIFACT_CREATED" in types
    assert "SRP_MERGE_READY" in types
    replay_result = replay(tmp_path / "runtime")
    assert replay_result.ok is True
    srp = replay_result.state["activity"]["srp"]
    assert srp["apply_requests"] == 1
    assert srp["approvals_verified"] == 1
    assert srp["merge_ready_marked"] == 1


def test_cleanup_does_not_delete_unrelated_files(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_git_repo(repo)
    unrelated = repo / "keep_me.txt"
    unrelated.write_text("stay", encoding="utf-8")
    subprocess.run(["git", "add", "keep_me.txt"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "add keep"], cwd=repo, check=True, capture_output=True)
    bundle, approval, patch = _bundle_and_approval(tmp_path)
    result = run_approval_review_apply(
        bundle, approval, patch, repo_root=repo, proof_root=tmp_path / "proofs"
    )
    assert result.ok is True
    assert result.sandbox_path is not None
    sandbox_root = Path(result.sandbox_path).parent
    receipt = cleanup_sandbox(sandbox_root, repo)
    assert unrelated.read_text(encoding="utf-8") == "stay"
    assert receipt.get("worktree_removed") == "true" or receipt.get("directory_removed") == "true"


def test_closed_bundle_rejected(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_git_repo(repo)
    bundle, approval, patch = _bundle_and_approval(tmp_path)
    result = run_approval_review_apply(
        bundle,
        approval,
        patch,
        repo_root=repo,
        proof_root=tmp_path / "proofs",
        closed_bundle_ids=frozenset({bundle.bundle_id}),
    )
    assert result.ok is False
    assert result.reason_code == "bundle_already_closed"
