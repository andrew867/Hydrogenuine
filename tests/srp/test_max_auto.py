"""Maximum autonomy maintenance module tests."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

from hg_runtime.bus import EventBus
from hg_runtime.replay import replay
from hg_srp.apply_types import ApprovedPatchBundle
from hg_srp.max_auto.bundle import create_max_auto_bundle
from hg_srp.max_auto.command_policy import evaluate_argv
from hg_srp.max_auto.config import MaxAutoConfig, MaxAutoConfigError
from hg_srp.max_auto.controller import run_max_auto_cycle
from hg_srp.max_auto.lifecycle import (
    STATE_IDLE,
    STATE_PATCHING,
    STATE_REFUSED,
    validate_max_auto_transition,
)
from hg_srp.max_auto.observations import ingest_from_operator_request
from hg_srp.max_auto.policy import check_run_policy
from hg_srp.max_auto.types import MaxAutoObservation, content_hash

NOW = "2026-06-12T02:00:00.000000Z"
SAFE_TEST = "tests/ter/test_safe_fixture.py"


def _obs(summary: str = "operator maintenance request") -> MaxAutoObservation:
    return ingest_from_operator_request(summary, observed_at=NOW)


def _config(tmp_path: Path, **overrides) -> MaxAutoConfig:
    base = {
        "enabled": True,
        "mode": "observe_only",
        "max_iterations": 3,
        "max_commands": 50,
        "allowed_tests": frozenset({SAFE_TEST}),
        "workdir": tmp_path / "work",
        "proof_dir": tmp_path / "proof",
        "require_confirmation": True,
        "allow_local_commit": False,
        "allow_push": False,
    }
    base.update(overrides)
    return MaxAutoConfig(**base)


def test_default_disabled():
    os.environ.pop("HG_SRP_MAX_AUTO_ENABLED", None)
    cfg = MaxAutoConfig.from_env()
    assert cfg.enabled is False


def test_allow_push_refuses_startup():
    os.environ["HG_SRP_MAX_AUTO_ALLOW_PUSH"] = "1"
    try:
        with pytest.raises(MaxAutoConfigError, match="unsupported_remote_push"):
            MaxAutoConfig.from_env()
    finally:
        os.environ.pop("HG_SRP_MAX_AUTO_ALLOW_PUSH", None)


def test_observe_only_does_not_mutate_files(tmp_path: Path):
    marker = tmp_path / "protected_marker.txt"
    marker.write_text("unchanged", encoding="utf-8")
    result = run_max_auto_cycle(
        [_obs()],
        config=_config(tmp_path),
        repo_root=tmp_path,
        clock=lambda: NOW,
    )
    assert result.ok is True
    assert marker.read_text(encoding="utf-8") == "unchanged"
    assert any(d["type"] == "MAX_AUTO_BUNDLE_CREATED" for d in result.rtc_drafts)


def test_proposal_only_creates_bundle_only(tmp_path: Path):
    cfg = _config(tmp_path, mode="proposal_only")
    result = run_max_auto_cycle([_obs()], config=cfg, repo_root=tmp_path, clock=lambda: NOW)
    assert result.ok is True
    assert result.verdict is not None
    assert result.verdict.verdict == "completed"


def test_push_always_refused_by_command_policy():
    result = evaluate_argv(("git", "push", "origin", "main"))
    assert result.allowed is False
    assert "push" in result.reason


def test_arbitrary_shell_refused():
    result = evaluate_argv(("bash", "-c", "echo hi"))
    assert result.allowed is False


def test_bundle_hash_deterministic(tmp_path: Path):
    obs = [_obs("same request")]
    b1 = create_max_auto_bundle(obs, created_at=NOW, required_tests=(SAFE_TEST,))
    b2 = create_max_auto_bundle(obs, created_at=NOW, required_tests=(SAFE_TEST,))
    assert b1.bundle_hash == b2.bundle_hash


def test_bundle_hash_changes_on_scope_change(tmp_path: Path):
    b1 = create_max_auto_bundle([_obs("one")], created_at=NOW, required_tests=(SAFE_TEST,))
    b2 = create_max_auto_bundle([_obs("two")], created_at=NOW, required_tests=(SAFE_TEST,))
    assert b1.bundle_hash != b2.bundle_hash


def test_illegal_lifecycle_transitions():
    assert validate_max_auto_transition(STATE_IDLE, STATE_PATCHING).ok is False
    assert validate_max_auto_transition(STATE_REFUSED, STATE_PATCHING).ok is False


def test_disabled_module_refuses(tmp_path: Path):
    cfg = _config(tmp_path, enabled=False)
    result = run_max_auto_cycle([_obs()], config=cfg, repo_root=tmp_path, clock=lambda: NOW)
    assert result.ok is False
    assert any(d["type"] == "MAX_AUTO_RUN_REFUSED" for d in result.rtc_drafts)


def test_high_risk_requires_confirmation(tmp_path: Path):
    obs = [_obs()]
    bundle = create_max_auto_bundle(
        obs,
        created_at=NOW,
        candidate_files=("hg_ter/policy.py",),
        required_tests=(SAFE_TEST,),
    )
    cfg = _config(tmp_path)
    policy = check_run_policy(cfg, bundle, operator_confirmed=False)
    assert policy.ok is False
    assert "high_risk" in policy.reason


def _init_git_repo(repo: Path) -> None:
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "gate@test"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "gate"], cwd=repo, check=True)
    (repo / "tests" / "ter").mkdir(parents=True, exist_ok=True)
    shutil.copy(Path(SAFE_TEST), repo / "tests" / "ter" / "test_safe_fixture.py")
    (repo / "marker.txt").write_text("before\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=repo, check=True, capture_output=True)


def _patch(bundle_hash: str) -> ApprovedPatchBundle:
    return ApprovedPatchBundle(
        patch_id="patch-1",
        bundle_ref="bundle-1",
        bundle_hash=bundle_hash,
        format="file_overlay",
        file_overlays=(("marker.txt", "after\n"),),
        test_commands=(SAFE_TEST,),
    )


def test_sandbox_apply_mutates_worktree_only(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_git_repo(repo)
    obs = [_obs("sandbox apply test")]
    bundle = create_max_auto_bundle(obs, created_at=NOW, required_tests=(str(repo / SAFE_TEST).replace("\\", "/") if False else SAFE_TEST,))
    cfg = MaxAutoConfig(
        enabled=True,
        mode="sandbox_apply",
        max_iterations=1,
        max_commands=50,
        allowed_tests=frozenset({SAFE_TEST}),
        workdir=tmp_path / "work",
        proof_dir=tmp_path / "proof",
        require_confirmation=False,
        allow_local_commit=False,
    )
    patch = _patch(bundle.bundle_hash)
    result = run_max_auto_cycle(
        obs,
        config=cfg,
        repo_root=repo,
        patch=patch,
        clock=lambda: NOW,
    )
    assert (repo / "marker.txt").read_text(encoding="utf-8") == "before\n"
    assert result.verdict is not None
    assert result.verdict.remote_push_occurred is False
    assert result.verdict.deploy_occurred is False


def test_rtc_events_replay(tmp_path: Path):
    runtime_dir = tmp_path / "runtime"
    bus = EventBus(runtime_dir, clock=lambda: NOW)
    result = run_max_auto_cycle(
        [_obs()],
        config=_config(tmp_path),
        repo_root=tmp_path,
        clock=lambda: NOW,
    )
    for draft in result.rtc_drafts:
        bus.emit_draft(draft, source="srp:max_auto")
    replay_result = replay(runtime_dir)
    assert replay_result.ok is True
    assert replay_result.state["activity"]["max_auto"]["bundles_created"] >= 1


def test_module_disabled_by_default_env():
    os.environ.pop("HG_SRP_MAX_AUTO_ENABLED", None)
    assert MaxAutoConfig.from_env().enabled is False
