"""GitHub deploy key generation (OpenSSH Ed25519)."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from hg_runtime.github_anchor_repo_init.hygiene import restrict_private_permissions, verify_key_hygiene
from hg_runtime.github_anchor_repo_init.paths import DEFAULT_DEPLOY_KEY_DIR, DEFAULT_DEPLOY_KEY_STEM, WORKSPACE


@dataclass
class DeployKeyResult:
    private_key_path: Path
    public_key_path: Path
    public_key_contents: str
    created: bool
    verdict: str
    instructions: list[str]

    def to_payload(self) -> dict:
        return {
            "schema": "github-deploy-key-init",
            "verdict": self.verdict,
            "private_key_path": "[REDACTED]",
            "public_key_path": str(self.public_key_path),
            "public_key_contents": self.public_key_contents,
            "created": self.created,
            "instructions": self.instructions,
            "private_key_printed": False,
            "advisory_only": True,
            "permission_granted": False,
            "authority_created": False,
        }


def generate_deploy_key(
    *,
    out_dir: Path | None = None,
    comment: str = "agent-zero-anchor@hydrogenuine",
    no_passphrase: bool = True,
    force: bool = False,
) -> DeployKeyResult:
    base = out_dir or DEFAULT_DEPLOY_KEY_DIR
    base.mkdir(parents=True, exist_ok=True)
    private_path = base / DEFAULT_DEPLOY_KEY_STEM
    public_path = Path(str(private_path) + ".pub")
    created = False

    if private_path.exists() and force:
        private_path.unlink(missing_ok=True)
        public_path.unlink(missing_ok=True)

    if private_path.exists() and not force:
        public_pem = public_path.read_text(encoding="utf-8").strip() if public_path.exists() else ""
        hygiene = verify_key_hygiene(private_path, workspace=WORKSPACE)
        if hygiene["private_key_tracked"]:
            raise ValueError("RED_PRIVATE_KEY_TRACKED")
        return DeployKeyResult(
            private_key_path=private_path,
            public_key_path=public_path,
            public_key_contents=public_pem,
            created=False,
            verdict="GREEN_GITHUB_DEPLOY_KEY_READY",
            instructions=_github_instructions(public_pem),
        )

    cmd = [
        "ssh-keygen",
        "-t",
        "ed25519",
        "-C",
        comment,
        "-f",
        str(private_path),
    ]
    if no_passphrase:
        cmd.extend(["-N", ""])
    if force and private_path.exists():
        cmd.append("-y")  # not valid with -f for regen; remove and use -f only
        cmd = [c for c in cmd if c != "-y"]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0 and not (private_path.exists() and public_path.exists()):
        raise RuntimeError(f"ssh-keygen failed: {proc.stderr.strip()}")
    created = True
    restrict_private_permissions(private_path)
    public_contents = public_path.read_text(encoding="utf-8").strip()
    hygiene = verify_key_hygiene(private_path, workspace=WORKSPACE)
    if hygiene["private_key_tracked"]:
        raise ValueError("RED_PRIVATE_KEY_TRACKED")
    return DeployKeyResult(
        private_key_path=private_path,
        public_key_path=public_path,
        public_key_contents=public_contents,
        created=created,
        verdict="GREEN_GITHUB_DEPLOY_KEY_READY",
        instructions=_github_instructions(public_contents),
    )


def _github_instructions(public_key: str) -> list[str]:
    return [
        "GitHub → Repo → Settings → Deploy keys → Add deploy key",
        "Title: Agent Zero Anchor Writer",
        f"Key: {public_key}",
        "Enable Allow write access",
    ]


__all__ = ["DeployKeyResult", "generate_deploy_key"]
