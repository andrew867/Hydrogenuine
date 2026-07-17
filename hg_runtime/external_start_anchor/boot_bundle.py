"""Build sanitized BootContinuityBundle from local workspace state."""

from __future__ import annotations

import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hg_runtime.external_start_anchor.canonical_json import sha256_hex
from hg_runtime.external_start_anchor.schema import BootContinuityBundle, GitHubAnchorConfig
from hg_runtime.trust_boundary.secrets import SecretGuard

WORKSPACE = Path(__file__).resolve().parents[2]

FORBIDDEN_PATH_FRAGMENTS = (
    ".env",
    ".hg-local",
    "credentials",
    "secret",
    "cookie",
    "session",
    "audio_models",
    "openvino-provider",
)


def _git(args: list[str], cwd: Path) -> tuple[int, str]:
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    out = (result.stdout or result.stderr or "").strip()
    return result.returncode, out


def _workspace_git_head(workspace: Path) -> tuple[str, str]:
    rc, head = _git(["rev-parse", "HEAD"], workspace)
    if rc != 0:
        return "", ""
    _, branch = _git(["branch", "--show-current"], workspace)
    return head, branch


def _sanitize_note(note: str | None) -> str | None:
    if not note:
        return None
    if SecretGuard.contains_secret(note):
        raise ValueError("operator note contains secret-shaped content")
    cleaned = note.strip()
    for frag in FORBIDDEN_PATH_FRAGMENTS:
        if frag in cleaned.lower():
            raise ValueError(f"operator note contains forbidden fragment: {frag}")
    return cleaned


def _hash_file(path: Path) -> str | None:
    if not path.is_file():
        return None
    return sha256_hex(json.loads(path.read_text(encoding="utf-8")))


def build_boot_bundle(
    cfg: GitHubAnchorConfig,
    *,
    workspace: Path | None = None,
    sequence: int = 0,
    chrono_receipt_ref: str | None = None,
    epoch_lock_id: str | None = None,
    operator_note: str | None = None,
    previous_anchor_sha256: str | None = None,
    previous_github_commit: str | None = None,
) -> BootContinuityBundle:
    ws = workspace or WORKSPACE
    head, branch = _workspace_git_head(ws)
    now = datetime.now(timezone.utc).isoformat()
    note = _sanitize_note(operator_note)
    return BootContinuityBundle(
        agent_long_name=cfg.agent_long_name,
        agent_short_name=cfg.agent_short_name,
        agent_code_id=cfg.agent_code_id,
        anchor_sequence=sequence,
        created_utc=now,
        chrono_receipt_ref=chrono_receipt_ref,
        epoch_lock_id=epoch_lock_id,
        hydrogenuine_repo_head=head,
        hydrogenuine_branch=branch,
        baseline_gate_refs=[
            "authority_chain",
            "trust_boundary",
            "chrono_time_sync",
            "will_module_final",
        ],
        operator_public_note=note,
        previous_anchor_sha256=previous_anchor_sha256,
        previous_github_commit=previous_github_commit,
        secrets_included=False,
    )


def assert_bundle_safe(bundle: BootContinuityBundle) -> None:
    payload = json.dumps(bundle.to_dict())
    if SecretGuard.contains_secret(payload):
        raise ValueError("boot bundle contains secret-shaped content")
    if bundle.secrets_included:
        raise ValueError("secrets_included must be false")
    if bundle.permission_granted or bundle.authority_created:
        raise ValueError("authority conversion in boot bundle")
    if re.search(r"(?i)\.env|api[_-]?key|password\s*=", payload):
        raise ValueError("boot bundle contains forbidden patterns")


__all__ = ["assert_bundle_safe", "build_boot_bundle"]
