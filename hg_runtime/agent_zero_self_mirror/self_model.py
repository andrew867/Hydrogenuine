"""Canonical self model snapshot."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from hg_runtime.agent_zero_self_mirror.capability_reader import build_capability_index
from hg_runtime.agent_zero_self_mirror.organ_reader import build_organ_index, organ_manifest_hash
from hg_runtime.agent_zero_self_mirror.repo_index import WORKSPACE, _git_head, snapshot_hash
from hg_runtime.agent_zero_self_mirror.schema import SelfModelSnapshot
from hg_runtime.tool_capability_fabric.registry import load_registry

FORBIDDEN_DIRECT = [
    "modify_source_code",
    "commit_code",
    "edit_memory_directly",
    "execute_privileged_shell",
    "grant_self_permission",
    "publish_externally",
    "read_env_secrets",
    "read_browser_sessions",
]

READ_ONLY_VIEWS = [
    "source_index",
    "docs_index",
    "config_index",
    "proof_index",
    "datastore_index",
    "capability_index",
    "organ_index",
    "identity_continuity",
    "chrono_lock",
    "external_anchor",
    "will_profile",
]

TOOL_REQUEST_PATHS = [
    "tool_capability_fabric.broker",
    "memory_tool_contracts",
    "governed_tool_request",
]


def _hash_file(path: Path) -> str | None:
    if not path.is_file():
        return None
    try:
        return snapshot_hash(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError):
        return None


def build_self_snapshot(
    *,
    workspace: Path | None = None,
    anchor_handoff: dict[str, Any] | None = None,
    chrono_lock: dict[str, Any] | None = None,
    will_profile_path: str | Path | None = None,
) -> SelfModelSnapshot:
    ws = workspace or WORKSPACE
    head, branch = _git_head(ws)
    cap_reg = load_registry()
    cap_manifest = cap_reg.build_manifest(organ_id="organ:Agent0", role="agent0")
    anchor = anchor_handoff or {}
    lock = chrono_lock or {}
    will_path = Path(will_profile_path) if will_profile_path else ws / "configs/will/agent0_dev_boot_will.example.json"
    return SelfModelSnapshot(
        repo_head=head,
        branch=branch,
        boot_epoch_id=lock.get("epoch_id"),
        chrono_lock_id=lock.get("epoch_lock_id"),
        external_anchor_status=anchor.get("verification_status") or "not_anchored",
        will_profile_hash=_hash_file(will_path),
        trust_boundary_policy_hash="trust_boundary/held",
        capability_manifest_hash=cap_manifest.get("manifest_hash"),
        organ_manifest_hash=organ_manifest_hash(),
        provider_status_hash=None,
        storage_status_hash="storage_artifact_vector/governed",
        audio_io_status_hash="audio_io/local",
        available_read_only_views=list(READ_ONLY_VIEWS),
        available_tool_request_paths=list(TOOL_REQUEST_PATHS),
        forbidden_direct_actions=list(FORBIDDEN_DIRECT),
    )


def snapshot_content_hash(snapshot: SelfModelSnapshot) -> str:
    return snapshot_hash(snapshot.to_payload())


__all__ = ["FORBIDDEN_DIRECT", "READ_ONLY_VIEWS", "build_self_snapshot", "snapshot_content_hash"]
