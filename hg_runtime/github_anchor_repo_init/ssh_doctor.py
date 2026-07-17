"""SSH doctor for GitHub anchor deploy key."""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

from hg_runtime.github_anchor_repo_init.hygiene import scrub_output, verify_key_hygiene
from hg_runtime.github_anchor_repo_init.paths import WORKSPACE, anchor_remote, deploy_key_private, deploy_key_public, live_ssh_test_enabled


@dataclass
class SSHDoctorResult:
    private_key_exists: bool
    public_key_exists: bool
    private_key_tracked: bool
    private_key_gitignored: bool
    ssh_auth_ok: bool | None
    ls_remote_ok: bool | None
    verdict: str
    detail: str

    def to_payload(self) -> dict:
        return {
            "schema": "github-anchor-ssh-doctor",
            "verdict": self.verdict,
            "private_key_exists": self.private_key_exists,
            "public_key_exists": self.public_key_exists,
            "private_key_tracked": self.private_key_tracked,
            "private_key_gitignored": self.private_key_gitignored,
            "ssh_auth_ok": self.ssh_auth_ok,
            "ls_remote_ok": self.ls_remote_ok,
            "detail": self.detail,
            "private_key_printed": False,
            "advisory_only": True,
            "permission_granted": False,
            "authority_created": False,
        }


def _ssh_command(private_path: Path) -> str:
    return f'ssh -i "{private_path}" -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new'


def run_ssh_doctor(
    *,
    private_key_path: Path | None = None,
    remote: str | None = None,
    live_test: bool | None = None,
) -> SSHDoctorResult:
    private_path = private_key_path or deploy_key_private()
    public_path = deploy_key_public()
    if not private_path.is_absolute():
        private_path = WORKSPACE / private_path
    if not public_path.is_absolute():
        public_path = WORKSPACE / public_path

    hygiene = verify_key_hygiene(private_path, workspace=WORKSPACE)
    priv_exists = private_path.exists()
    pub_exists = public_path.exists()

    if not priv_exists or not pub_exists:
        return SSHDoctorResult(
            private_key_exists=priv_exists,
            public_key_exists=pub_exists,
            private_key_tracked=hygiene["private_key_tracked"],
            private_key_gitignored=hygiene["private_key_gitignored"],
            ssh_auth_ok=None,
            ls_remote_ok=None,
            verdict="YELLOW_GITHUB_DEPLOY_KEY_NOT_ADDED_TO_REPO",
            detail="deploy key files missing — run deploy key init first",
        )

    if hygiene["private_key_tracked"]:
        return SSHDoctorResult(
            private_key_exists=True,
            public_key_exists=pub_exists,
            private_key_tracked=True,
            private_key_gitignored=hygiene["private_key_gitignored"],
            ssh_auth_ok=None,
            ls_remote_ok=None,
            verdict="RED_PRIVATE_KEY_TRACKED",
            detail="private deploy key is git-tracked",
        )

    do_live = live_ssh_test_enabled() if live_test is None else live_test
    if not do_live:
        return SSHDoctorResult(
            private_key_exists=True,
            public_key_exists=True,
            private_key_tracked=False,
            private_key_gitignored=hygiene["private_key_gitignored"],
            ssh_auth_ok=None,
            ls_remote_ok=None,
            verdict="YELLOW_GITHUB_DEPLOY_KEY_NOT_ADDED_TO_REPO",
            detail="live SSH test disabled — set HG_GITHUB_ANCHOR_LIVE_SSH_TEST=true",
        )

    ssh_cmd = _ssh_command(private_path)
    env = {"GIT_SSH_COMMAND": ssh_cmd}
    ssh_proc = subprocess.run(
        ["ssh", "-i", str(private_path), "-o", "IdentitiesOnly=yes", "-o", "StrictHostKeyChecking=accept-new", "-T", "git@github.com"],
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    ssh_out = scrub_output((ssh_proc.stdout or "") + (ssh_proc.stderr or ""), private_key_path=private_path)
    ssh_ok = ssh_proc.returncode in {0, 1} and (
        "successfully authenticated" in ssh_out.lower() or "hi " in ssh_out.lower() or "permission denied" not in ssh_out.lower()
    )

    remote_url = remote or anchor_remote()
    ls_ok = None
    if remote_url:
        ls_proc = subprocess.run(
            ["git", "ls-remote", remote_url],
            capture_output=True,
            text=True,
            check=False,
            env={**os.environ.copy(), "GIT_SSH_COMMAND": ssh_cmd},
            timeout=60,
        )
        ls_out = scrub_output((ls_proc.stdout or "") + (ls_proc.stderr or ""), private_key_path=private_path)
        ls_ok = ls_proc.returncode == 0
        if not ls_ok and "permission denied" in ls_out.lower():
            return SSHDoctorResult(
                private_key_exists=True,
                public_key_exists=True,
                private_key_tracked=False,
                private_key_gitignored=hygiene["private_key_gitignored"],
                ssh_auth_ok=ssh_ok,
                ls_remote_ok=False,
                verdict="YELLOW_GITHUB_DEPLOY_KEY_NOT_ADDED_TO_REPO",
                detail=ls_out[:300],
            )
        if not ls_ok:
            return SSHDoctorResult(
                private_key_exists=True,
                public_key_exists=True,
                private_key_tracked=False,
                private_key_gitignored=hygiene["private_key_gitignored"],
                ssh_auth_ok=ssh_ok,
                ls_remote_ok=False,
                verdict="RED_GITHUB_AUTH_FAILED",
                detail=ls_out[:300],
            )

    verdict = "GREEN_GITHUB_SSH_PUSH_READY" if ls_ok else (
        "YELLOW_GITHUB_DEPLOY_KEY_NOT_ADDED_TO_REPO" if not ssh_ok else "GREEN_GITHUB_SSH_PUSH_READY"
    )
    return SSHDoctorResult(
        private_key_exists=True,
        public_key_exists=True,
        private_key_tracked=False,
        private_key_gitignored=hygiene["private_key_gitignored"],
        ssh_auth_ok=ssh_ok,
        ls_remote_ok=ls_ok,
        verdict=verdict,
        detail="ssh doctor complete",
    )


__all__ = ["SSHDoctorResult", "run_ssh_doctor"]
