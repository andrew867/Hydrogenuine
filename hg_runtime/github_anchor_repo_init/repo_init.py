"""Initialize local GitHub witness anchor repository layout."""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

from hg_runtime.external_start_anchor.credentials import git_subprocess_env
from hg_runtime.github_anchor_repo_init.paths import WORKSPACE, anchor_branch, anchor_remote, anchor_repo_path, push_allowed


WITNESS_README = """# Hydrogenuine Agent Zero Witness Anchor

Public hash witness repository for Agent Zero external start anchors and witness journal.

- Public hash witness only — no secrets, no credentials, no private keys.
- No authority minted here. No permission granted. Advisory evidence only.
- Public signing keys may be published under `anchors/agent0/keys/`.
"""

ANCHOR_README = """# Agent Zero Start Anchors

Committed public anchor bundles only. Private signing keys never belong in this repo.
"""

JOURNAL_README = """# Agent Zero Witness Journal

Append-only hash-chained witness events. Evidence only — not commands.
"""

KEYS_README = """# Agent Zero Anchor Signing Public Keys

Published public keys only. Never commit private keys or deploy key material.
"""

WITNESS_GITIGNORE = """# Local operator temp files
*.tmp
*.local
.env
*.pem
*.key
id_*
"""


@dataclass
class RepoInitResult:
    repo_path: Path
    branch: str
    remote: str
    initial_commit_sha: str | None
    pushed: bool
    verdict: str

    def to_payload(self) -> dict:
        return {
            "schema": "github-anchor-repo-init",
            "verdict": self.verdict,
            "repo_path": str(self.repo_path),
            "branch": self.branch,
            "remote": self.remote or None,
            "initial_commit_sha": self.initial_commit_sha,
            "pushed": self.pushed,
            "advisory_only": True,
            "permission_granted": False,
            "authority_created": False,
        }


def _run_git(args: list[str], cwd: Path, *, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    if any(a in args for a in ("--force", "-f")) and "push" in args:
        raise ValueError("RED_FORCE_PUSH_AVAILABLE")
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=False, env=env)


def _write_layout(repo: Path) -> None:
    (repo / "README.md").write_text(WITNESS_README, encoding="utf-8")
    (repo / ".gitignore").write_text(WITNESS_GITIGNORE, encoding="utf-8")
    anchor = repo / "anchors" / "agent0"
    journal = repo / "anchors" / "agent0_journal"
    keys = anchor / "keys"
    for d in (anchor, journal, keys, anchor / "history", journal / "events"):
        d.mkdir(parents=True, exist_ok=True)
    (anchor / "README.md").write_text(ANCHOR_README, encoding="utf-8")
    (journal / "README.md").write_text(JOURNAL_README, encoding="utf-8")
    (keys / "README.md").write_text(KEYS_README, encoding="utf-8")
    latest = {
        "schema": "agent-zero-start-anchor-placeholder",
        "anchor_sequence": -1,
        "status": "uninitialized",
        "advisory_only": True,
        "permission_granted": False,
        "authority_created": False,
    }
    (anchor / "latest.json").write_text(json.dumps(latest, indent=2) + "\n", encoding="utf-8")
    chain = {
        "schema": "agent-zero-witness-journal-chain",
        "events": [],
        "advisory_only": True,
        "permission_granted": False,
        "authority_created": False,
    }
    (journal / "chain.json").write_text(json.dumps(chain, indent=2) + "\n", encoding="utf-8")


def init_witness_repo(
    *,
    repo_path: Path | None = None,
    remote: str | None = None,
    branch: str | None = None,
    push: bool = False,
) -> RepoInitResult:
    repo = repo_path or anchor_repo_path()
    if not repo.is_absolute():
        repo = (WORKSPACE / repo).resolve()
    branch = branch or anchor_branch()
    remote = remote if remote is not None else anchor_remote()
    repo.mkdir(parents=True, exist_ok=True)

    if not (repo / ".git").exists():
        _run_git(["init", "-b", branch], repo)

    _write_layout(repo)

    env = git_subprocess_env()
    if remote:
        existing = _run_git(["remote"], repo, env=env)
        if "origin" not in (existing.stdout or "").split():
            _run_git(["remote", "add", "origin", remote], repo, env=env)
        else:
            _run_git(["remote", "set-url", "origin", remote], repo, env=env)

    status = _run_git(["status", "--porcelain"], repo, env=env)
    commit_sha = None
    if status.stdout.strip():
        _run_git(["add", "-A"], repo, env=env)
        _run_git(["commit", "-m", "chore(anchor): initialize witness repo layout"], repo, env=env)
        head = _run_git(["rev-parse", "HEAD"], repo, env=env)
        commit_sha = head.stdout.strip() if head.returncode == 0 else None
    else:
        head = _run_git(["rev-parse", "HEAD"], repo, env=env)
        commit_sha = head.stdout.strip() if head.returncode == 0 else None

    pushed = False
    if push:
        if not push_allowed():
            raise PermissionError("push requires HG_ANCHOR_ALLOW_PUSH=true")
        if not remote:
            raise ValueError("remote required for push")
        push_proc = _run_git(["push", "-u", "origin", branch], repo, env=env)
        if push_proc.returncode != 0:
            raise RuntimeError(push_proc.stderr.strip() or "push failed")
        pushed = True
        _run_git(["fetch", "origin"], repo, env=env)

    return RepoInitResult(
        repo_path=repo,
        branch=branch,
        remote=remote,
        initial_commit_sha=commit_sha,
        pushed=pushed,
        verdict="GREEN_GITHUB_ANCHOR_REPO_INIT_READY",
    )


__all__ = ["RepoInitResult", "init_witness_repo"]
