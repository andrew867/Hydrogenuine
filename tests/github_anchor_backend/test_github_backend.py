"""GitHub git backend dry-run tests with local temp repos."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from hg_runtime.external_start_anchor.boot_bundle import build_boot_bundle
from hg_runtime.external_start_anchor.github_git_backend import AnchorRepoDirty, GitHubGitBackend
from hg_runtime.external_start_anchor.public_anchor import build_public_anchor
from hg_runtime.external_start_anchor.schema import GitHubAnchorConfig


def _git(args: list[str], cwd: Path) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


@pytest.fixture
def anchor_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "anchor"
    repo.mkdir()
    _git(["init", "-b", "main"], repo)
    _git(["config", "user.email", "anchor@test.local"], repo)
    _git(["config", "user.name", "Anchor Test"], repo)
    (repo / "README.md").write_text("# anchor\n", encoding="utf-8")
    _git(["add", "README.md"], repo)
    _git(["commit", "-m", "init"], repo)
    return repo


def test_dry_run_writes_expected_files(anchor_repo: Path):
    cfg = GitHubAnchorConfig(anchor_repo_path=str(anchor_repo), allow_push=False)
    boot = build_boot_bundle(cfg, sequence=0)
    public = build_public_anchor(boot)
    backend = GitHubGitBackend(cfg, workspace=anchor_repo.parent)
    result = backend.publish(public, dry_run=True)
    assert result.dry_run is True
    assert result.pushed is False
    dry = anchor_repo.parent / ".hg-local" / "external_start_anchor" / "dry_run_repo"
    assert (dry / cfg.sequence_file).exists()


def test_refuses_dirty_anchor_repo(anchor_repo: Path):
    cfg = GitHubAnchorConfig(anchor_repo_path=str(anchor_repo), allow_push=True, require_clean_anchor_repo=True)
    (anchor_repo / "dirty.txt").write_text("x", encoding="utf-8")
    backend = GitHubGitBackend(cfg, workspace=anchor_repo.parent)
    boot = build_boot_bundle(cfg, sequence=0)
    public = build_public_anchor(boot)
    with pytest.raises(AnchorRepoDirty):
        backend.publish(public, dry_run=False, push=True)


def test_local_commit_records_sha(anchor_repo: Path):
    cfg = GitHubAnchorConfig(
        anchor_repo_path=str(anchor_repo),
        allow_push=True,
        require_clean_anchor_repo=True,
        anchor_repo_remote="",
    )
    boot = build_boot_bundle(cfg, sequence=0)
    public = build_public_anchor(boot)
    backend = GitHubGitBackend(cfg, workspace=anchor_repo.parent)
    # simulate push locally without remote
    paths = backend.write_anchor_files if False else None  # noqa: F841
    from hg_runtime.external_start_anchor.github_git_backend import write_anchor_files

    write_anchor_files(anchor_repo, cfg, public)
    _git(["add", "."], anchor_repo)
    _git(["commit", "-m", "anchor(agent0): sequence 0 test"], anchor_repo)
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=anchor_repo, text=True).strip()
    fetched = json.loads((anchor_repo / cfg.sequence_file).read_text(encoding="utf-8"))
    assert fetched["boot_bundle_sha256"] == public.boot_bundle_sha256
    assert len(head) == 40
