"""Push smoke test for witness anchor repo."""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from hg_runtime.external_start_anchor.credentials import assert_no_secret_in_payload, git_subprocess_env
from hg_runtime.github_anchor_repo_init.paths import WORKSPACE, anchor_branch, anchor_remote, anchor_repo_path, push_allowed
from hg_runtime.github_anchor_repo_init.repo_init import init_witness_repo


@dataclass
class PushSmokeResult:
    repo_path: Path
    commit_sha: str | None
    remote_sha: str | None
    pushed: bool
    verdict: str

    def to_payload(self) -> dict:
        payload = {
            "schema": "github-anchor-push-smoke",
            "verdict": self.verdict,
            "repo_path": str(self.repo_path),
            "commit_sha": self.commit_sha,
            "remote_sha": self.remote_sha,
            "pushed": self.pushed,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "advisory_only": True,
            "permission_granted": False,
            "authority_created": False,
        }
        assert_no_secret_in_payload(payload)
        return payload


def run_push_smoke(*, push: bool = True) -> PushSmokeResult:
    if push and not push_allowed():
        return PushSmokeResult(
            repo_path=anchor_repo_path(),
            commit_sha=None,
            remote_sha=None,
            pushed=False,
            verdict="YELLOW_LIVE_PUSH_NOT_TESTED",
        )

    init = init_witness_repo(push=False)
    repo = init.repo_path
    env = git_subprocess_env()
    branch = anchor_branch()
    remote = anchor_remote()

    marker = repo / "anchors" / "agent0" / ".push_smoke_receipt.json"
    marker.write_text(
        json.dumps(
            {
                "schema": "anchor-push-smoke-receipt",
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "advisory_only": True,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    subprocess.run(["git", "add", "-A"], cwd=repo, check=False, env=env)
    subprocess.run(["git", "commit", "-m", "chore(anchor): push smoke receipt"], cwd=repo, check=False, env=env)
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True, check=False, env=env)
    commit_sha = head.stdout.strip() if head.returncode == 0 else None

    pushed = False
    remote_sha = None
    if push and remote:
        push_proc = subprocess.run(
            ["git", "push", "-u", "origin", branch],
            cwd=repo,
            capture_output=True,
            text=True,
            check=False,
            env=env,
        )
        if push_proc.returncode != 0:
            raise RuntimeError(push_proc.stderr.strip() or "push failed")
        pushed = True
        ls = subprocess.run(
            ["git", "ls-remote", remote, f"refs/heads/{branch}"],
            capture_output=True,
            text=True,
            check=False,
            env=env,
        )
        if ls.returncode == 0 and ls.stdout.strip():
            remote_sha = ls.stdout.split()[0]

    receipt_dir = WORKSPACE / ".hg-local" / "external_start_anchor"
    receipt_dir.mkdir(parents=True, exist_ok=True)
    result = PushSmokeResult(
        repo_path=repo,
        commit_sha=commit_sha,
        remote_sha=remote_sha,
        pushed=pushed,
        verdict="GREEN_GITHUB_SSH_PUSH_READY" if pushed else "YELLOW_LIVE_PUSH_NOT_TESTED",
    )
    (receipt_dir / "push_smoke_receipt.json").write_text(json.dumps(result.to_payload(), indent=2) + "\n", encoding="utf-8")
    return result


__all__ = ["PushSmokeResult", "run_push_smoke"]
