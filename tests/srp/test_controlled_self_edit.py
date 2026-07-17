"""SRP controlled self-edit gate tests — guarded gremlin mode."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from hg_runtime.bus import EventBus
from hg_runtime.replay import replay
from hg_srp import (
    APPLY_MODE_COMMIT_ONLY,
    ApprovedPatchBundle,
    ChangeApprovalSignature,
    FinalConfirmationToken,
    create_maintenance_bundle,
    ingest_pytest_failure_artifact,
    run_approval_review_apply,
    run_controlled_self_edit,
    validate_self_edit_transition,
)
from hg_srp.apply_types import ReviewArtifact, content_hash
from hg_srp.self_edit_lifecycle import (
    STATE_FINAL_CONFIRMATION_VERIFIED,
    STATE_MERGE_STARTED,
    STATE_REVIEW_CREATED,
    STATE_SIGNED,
)
from hg_srp.self_edit_policy import reset_self_edit_registries
from hg_srp.self_edit_rtc_bridge import emit_self_edit_workflow
from hg_srp.sandbox import protected_head_hash
from hg_ter import TERExecutor
from hg_ter.types import CommandRequest

NOW = "2026-06-11T16:00:00.000000Z"
FIXTURES = Path(__file__).parent / "fixtures"
SAFE_TEST = Path(__file__).parents[1] / "ter" / "test_safe_fixture.py"


@pytest.fixture(autouse=True)
def _reset_registries():
    reset_self_edit_registries()
    yield
    reset_self_edit_registries()


def _init_git_repo(repo: Path) -> str:
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "gremlin@test"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "gremlin-test"], cwd=repo, check=True)
    (repo / "tests" / "ter").mkdir(parents=True, exist_ok=True)
    shutil.copy(SAFE_TEST, repo / "tests" / "ter" / "test_safe_fixture.py")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=repo, check=True, capture_output=True)
    return protected_head_hash(repo) or ""


def _setup_bundle_patch():
    obs = ingest_pytest_failure_artifact(FIXTURES / "pytest_failure_sample.json", observed_at=NOW)
    bundle = create_maintenance_bundle([obs], created_at=NOW)
    approval = ChangeApprovalSignature(
        approval_id="apr-gremlin-1",
        proposal_ref=bundle.bundle_id,
        bundle_hash=bundle.bundle_hash,
        approver="human:operator",
        decision="approved",
        decided_at=NOW,
    )
    patch = ApprovedPatchBundle(
        patch_id="patch-gremlin-1",
        bundle_ref=bundle.bundle_id,
        bundle_hash=bundle.bundle_hash,
        format="file_overlay",
        file_overlays=(("docs/gremlin_marker.txt", "# controlled self-edit marker\n"),),
        test_commands=("tests/ter/test_safe_fixture.py",),
    )
    return bundle, approval, patch


def _run_sandbox(repo: Path, bundle, approval, patch, proof_root: Path):
    return run_approval_review_apply(
        bundle, approval, patch, repo_root=repo, proof_root=proof_root,
    )


def _load_review(apply_result) -> ReviewArtifact:
    data = json.loads(Path(apply_result.review_artifact_path).read_text(encoding="utf-8"))
    return ReviewArtifact(
        artifact_id=data["artifact_id"],
        bundle_id=data["bundle_id"],
        bundle_hash=data["bundle_hash"],
        patch_hash=data["patch_hash"],
        sandbox_path=data["sandbox_path"],
        sandbox_branch=data["sandbox_branch"],
        applied_files=tuple(data["applied_files"]),
        protected_head_before=data["protected_head_before"],
        protected_head_after=data["protected_head_after"],
        protected_unchanged=data["protected_unchanged"],
        test_results=tuple(data["test_results"]),
        merge_ready=data["merge_ready"],
        final_human_confirmation_required=data["final_human_confirmation_required"],
        autonomous_merge_enabled=data["autonomous_merge_enabled"],
        artifact_path=data["artifact_path"],
    )


def _make_confirmation(bundle, apply_result, review, base_commit, *, nonce="nonce-1", **kwargs):
    fields = {
        "bundle_id": bundle.bundle_id,
        "bundle_hash": bundle.bundle_hash,
        "sandbox_result_hash": content_hash(apply_result.to_payload()),
        "review_artifact_hash": review.artifact_hash,
        "base_commit": base_commit,
        "target_branch": "HEAD",
        "final_confirmed_by": "human:operator",
        "final_confirmed_at": NOW,
        "confirmation_nonce": nonce,
    }
    fields.update(kwargs)
    return FinalConfirmationToken(**fields)


def test_illegal_self_edit_transitions():
    assert validate_self_edit_transition(STATE_SIGNED, STATE_MERGE_STARTED).ok is False
    assert validate_self_edit_transition(STATE_REVIEW_CREATED, STATE_MERGE_STARTED).ok is False
    assert validate_self_edit_transition(STATE_FINAL_CONFIRMATION_VERIFIED, STATE_MERGE_STARTED).ok is False


def test_final_confirmation_separate_from_proposal_signature(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    base = _init_git_repo(repo)
    bundle, approval, patch = _setup_bundle_patch()
    apply_result = _run_sandbox(repo, bundle, approval, patch, tmp_path / "proofs")
    review = _load_review(apply_result)
    confirmation = _make_confirmation(bundle, apply_result, review, base)
    assert confirmation.confirmation_hash != approval.signature


def test_commit_only_self_edit_success(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    base = _init_git_repo(repo)
    bundle, approval, patch = _setup_bundle_patch()
    apply_result = _run_sandbox(repo, bundle, approval, patch, tmp_path / "proofs")
    assert apply_result.ok
    review = _load_review(apply_result)
    confirmation = _make_confirmation(bundle, apply_result, review, base)
    result = run_controlled_self_edit(
        bundle, approval, patch, apply_result, review, confirmation,
        apply_mode=APPLY_MODE_COMMIT_ONLY, repo_root=repo, proof_root=tmp_path / "proofs",
    )
    assert result.ok is True
    assert result.remote_push_occurred is False
    assert (repo / "docs" / "gremlin_marker.txt").exists()
    assert result.receipt_path is not None


def test_model_cannot_create_confirmation(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    base = _init_git_repo(repo)
    bundle, approval, patch = _setup_bundle_patch()
    apply_result = _run_sandbox(repo, bundle, approval, patch, tmp_path / "proofs")
    review = _load_review(apply_result)
    confirmation = _make_confirmation(
        bundle, apply_result, review, base, final_confirmed_by="model:gpt",
    )
    result = run_controlled_self_edit(
        bundle, approval, patch, apply_result, review, confirmation,
        repo_root=repo, proof_root=tmp_path / "proofs",
    )
    assert result.ok is False
    assert "model" in result.reason_code or "confirmation" in result.reason_code


def test_model_cannot_create_approval(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    base = _init_git_repo(repo)
    bundle, _, patch = _setup_bundle_patch()
    bad_approval = ChangeApprovalSignature(
        approval_id="apr-bad",
        proposal_ref=bundle.bundle_id,
        bundle_hash=bundle.bundle_hash,
        approver="model:gpt",
        decision="approved",
        decided_at=NOW,
    )
    apply_result = _run_sandbox(repo, bundle, bad_approval, patch, tmp_path / "proofs")
    assert apply_result.ok is False
    assert "model" in apply_result.reason_code
    assert apply_result.review_artifact_path is None


def test_reused_confirmation_refused(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    base = _init_git_repo(repo)
    bundle, approval, patch = _setup_bundle_patch()
    apply_result = _run_sandbox(repo, bundle, approval, patch, tmp_path / "proofs")
    review = _load_review(apply_result)
    confirmation = _make_confirmation(bundle, apply_result, review, base, nonce="reuse-me")
    r1 = run_controlled_self_edit(
        bundle, approval, patch, apply_result, review, confirmation,
        repo_root=repo, proof_root=tmp_path / "proofs",
    )
    assert r1.ok is True
    r2 = run_controlled_self_edit(
        bundle, approval, patch, apply_result, review, confirmation,
        repo_root=repo, proof_root=tmp_path / "proofs",
    )
    assert r2.ok is False
    assert r2.reason_code == "confirmation_nonce_reused"


def test_base_commit_mismatch_refused(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    base = _init_git_repo(repo)
    bundle, approval, patch = _setup_bundle_patch()
    apply_result = _run_sandbox(repo, bundle, approval, patch, tmp_path / "proofs")
    review = _load_review(apply_result)
    confirmation = _make_confirmation(bundle, apply_result, review, "deadbeef" * 5)
    result = run_controlled_self_edit(
        bundle, approval, patch, apply_result, review, confirmation,
        repo_root=repo, proof_root=repo / "proofs",
    )
    assert result.ok is False


def test_dirty_tree_refused(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    base = _init_git_repo(repo)
    bundle, approval, patch = _setup_bundle_patch()
    apply_result = _run_sandbox(repo, bundle, approval, patch, tmp_path / "proofs")
    review = _load_review(apply_result)
    (repo / "dirty.txt").write_text("x", encoding="utf-8")
    confirmation = _make_confirmation(bundle, apply_result, review, base)
    result = run_controlled_self_edit(
        bundle, approval, patch, apply_result, review, confirmation,
        repo_root=repo, proof_root=tmp_path / "proofs",
    )
    assert result.ok is False


def test_unsafe_git_push_blocked():
    executor = TERExecutor()
    request = CommandRequest(
        request_id="push-1",
        argv=("git", "push", "origin", "main"),
        cwd=str(Path.cwd()),
        requested_by="test",
        purpose="srp_self_edit_commit",
        created_at=NOW,
    )
    assert executor.evaluate(request).allowed is False


def test_high_risk_requires_extra_confirmation(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    base = _init_git_repo(repo)
    bundle, approval, patch = _setup_bundle_patch()
    risky_patch = ApprovedPatchBundle(
        patch_id="risky",
        bundle_ref=bundle.bundle_id,
        bundle_hash=bundle.bundle_hash,
        format="file_overlay",
        file_overlays=(("hg_srp/apply.py", "# tamper\n"),),
        test_commands=("tests/ter/test_safe_fixture.py",),
    )
    apply_result = _run_sandbox(repo, bundle, approval, risky_patch, tmp_path / "proofs")
    review = _load_review(apply_result)
    confirmation = _make_confirmation(bundle, apply_result, review, base, high_risk_confirmed=False)
    result = run_controlled_self_edit(
        bundle, approval, risky_patch, apply_result, review, confirmation,
        repo_root=repo, proof_root=tmp_path / "proofs",
    )
    assert result.ok is False
    assert result.reason_code == "high_risk_confirmation_required"


def test_self_edit_events_replay(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    base = _init_git_repo(repo)
    bundle, approval, patch = _setup_bundle_patch()
    apply_result = _run_sandbox(repo, bundle, approval, patch, tmp_path / "proofs")
    review = _load_review(apply_result)
    confirmation = _make_confirmation(bundle, apply_result, review, base, nonce="replay-nonce")
    result = run_controlled_self_edit(
        bundle, approval, patch, apply_result, review, confirmation,
        repo_root=repo, proof_root=tmp_path / "proofs",
    )
    bus = EventBus(tmp_path / "runtime", clock=lambda: NOW)
    emit_self_edit_workflow(bus, result)
    replay_result = replay(tmp_path / "runtime")
    assert replay_result.ok is True
    assert replay_result.state["activity"]["srp"]["self_edit_completed"] == 1


def test_no_remote_push_occurs(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    base = _init_git_repo(repo)
    bundle, approval, patch = _setup_bundle_patch()
    apply_result = _run_sandbox(repo, bundle, approval, patch, tmp_path / "proofs")
    review = _load_review(apply_result)
    confirmation = _make_confirmation(bundle, apply_result, review, base, nonce="no-push")
    result = run_controlled_self_edit(
        bundle, approval, patch, apply_result, review, confirmation,
        repo_root=repo, proof_root=tmp_path / "proofs",
    )
    assert result.remote_push_occurred is False
    receipt = json.loads(Path(result.receipt_path).read_text(encoding="utf-8"))
    assert receipt["remote_push_occurred"] is False
