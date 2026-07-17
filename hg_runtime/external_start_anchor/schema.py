"""External Start Anchor schema types."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

ANCHOR_SCHEMA_VERSION = "external_start_anchor/1"
PUBLIC_ANCHOR_TYPE = "HYDROGENUINE_AGENT_ZERO_GITHUB_ANCHOR_V1"

FROZEN_FALSE = {
    "advisory_only": True,
    "permission_granted": False,
    "authority_created": False,
}


class AnchorConfidence(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    UNKNOWN = "UNKNOWN"


class AnchorBackendStatus(str, Enum):
    READY = "READY"
    DRY_RUN = "DRY_RUN"
    NOT_AUTHENTICATED = "NOT_AUTHENTICATED"
    REMOTE_NOT_CONFIGURED = "REMOTE_NOT_CONFIGURED"
    PUSH_SKIPPED = "PUSH_SKIPPED"
    VERIFY_FAILED = "VERIFY_FAILED"
    SECRET_LEAK = "SECRET_LEAK"
    HASH_MISMATCH = "HASH_MISMATCH"


@dataclass
class GitHubAnchorConfig:
    enabled: bool = False
    anchor_id: str = "github-primary-dev"
    agent_long_name: str = "Agent Zero"
    agent_short_name: str = "Zero"
    agent_code_id: str = "agent0"
    primary_backend: str = "github_git"
    anchor_repo_path: str = "../hydrogenuine-agent-zero-anchor"
    anchor_repo_remote: str = ""
    anchor_branch: str = "main"
    anchor_public_dir: str = "anchors/agent0"
    sequence_file: str = "anchors/agent0/latest.json"
    history_dir: str = "anchors/agent0/history"
    allow_push: bool = False
    allow_create_repo: bool = False
    require_clean_anchor_repo: bool = True
    require_no_force_push: bool = True
    fetch_after_push: bool = True
    secondary_anchor_enabled: bool = False
    secondary_anchor_backend: str = "private_server_future"
    advisory_only: bool = True
    permission_granted: bool = False
    authority_created: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GitHubAnchorConfig:
        cfg = cls()
        for key, value in data.items():
            if key.startswith("_"):
                continue
            if hasattr(cfg, key):
                setattr(cfg, key, value)
        cfg._apply_env()
        return cfg

    def _apply_env(self) -> None:
        if os.environ.get("HG_ANCHOR_GITHUB_REPO_PATH") or os.environ.get("HG_GITHUB_ANCHOR_REPO_PATH"):
            self.anchor_repo_path = os.environ.get("HG_ANCHOR_GITHUB_REPO_PATH") or os.environ.get("HG_GITHUB_ANCHOR_REPO_PATH", self.anchor_repo_path)
        if os.environ.get("HG_ANCHOR_GITHUB_REMOTE") or os.environ.get("HG_GITHUB_ANCHOR_REPO_REMOTE"):
            remote = os.environ.get("HG_ANCHOR_GITHUB_REMOTE") or os.environ.get("HG_GITHUB_ANCHOR_REPO_REMOTE", "")
            if remote and not remote.startswith("git@") and not remote.startswith("https://"):
                remote = f"git@github.com:{remote}.git" if "/" in remote else remote
            self.anchor_repo_remote = remote
        if os.environ.get("HG_ANCHOR_GITHUB_BRANCH"):
            self.anchor_branch = os.environ["HG_ANCHOR_GITHUB_BRANCH"]
        if os.environ.get("HG_ANCHOR_ALLOW_PUSH", "").strip().lower() in {"1", "true", "yes", "on"}:
            self.allow_push = True
        if os.environ.get("HG_ANCHOR_ALLOW_CREATE_REPO", "").strip().lower() in {"1", "true", "yes", "on"}:
            self.allow_create_repo = True
        if os.environ.get("HG_ANCHOR_FETCH_AFTER_PUSH", "").strip().lower() in {"0", "false", "no", "off"}:
            self.fetch_after_push = False

    def resolved_repo_path(self, workspace: Path | None = None) -> Path:
        raw = Path(self.anchor_repo_path)
        if raw.is_absolute():
            return raw
        base = workspace or Path.cwd()
        return (base / raw).resolve()


@dataclass
class BootContinuityBundle:
    schema_version: str = ANCHOR_SCHEMA_VERSION
    agent_long_name: str = "Agent Zero"
    agent_short_name: str = "Zero"
    agent_code_id: str = "agent0"
    anchor_sequence: int = 0
    created_utc: str = ""
    chrono_receipt_ref: str | None = None
    epoch_lock_id: str | None = None
    hydrogenuine_repo_head: str = ""
    hydrogenuine_branch: str = ""
    baseline_gate_refs: list[str] = field(default_factory=list)
    will_profile_hash: str | None = None
    trust_boundary_policy_hash: str | None = None
    chrono_status_hash: str | None = None
    audio_io_status_hash: str | None = None
    model_provider_status_hash: str | None = None
    storage_status_hash: str | None = None
    operator_public_note: str | None = None
    previous_anchor_sha256: str | None = None
    previous_github_commit: str | None = None
    secrets_included: bool = False
    advisory_only: bool = True
    permission_granted: bool = False
    authority_created: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "agent_long_name": self.agent_long_name,
            "agent_short_name": self.agent_short_name,
            "agent_code_id": self.agent_code_id,
            "anchor_sequence": self.anchor_sequence,
            "created_utc": self.created_utc,
            "chrono_receipt_ref": self.chrono_receipt_ref,
            "epoch_lock_id": self.epoch_lock_id,
            "hydrogenuine_repo_head": self.hydrogenuine_repo_head,
            "hydrogenuine_branch": self.hydrogenuine_branch,
            "baseline_gate_refs": self.baseline_gate_refs,
            "will_profile_hash": self.will_profile_hash,
            "trust_boundary_policy_hash": self.trust_boundary_policy_hash,
            "chrono_status_hash": self.chrono_status_hash,
            "audio_io_status_hash": self.audio_io_status_hash,
            "model_provider_status_hash": self.model_provider_status_hash,
            "storage_status_hash": self.storage_status_hash,
            "operator_public_note": self.operator_public_note,
            "previous_anchor_sha256": self.previous_anchor_sha256,
            "previous_github_commit": self.previous_github_commit,
            "secrets_included": self.secrets_included,
            **FROZEN_FALSE,
        }


@dataclass
class PublicAnchorBundle:
    schema_version: str = ANCHOR_SCHEMA_VERSION
    anchor_type: str = PUBLIC_ANCHOR_TYPE
    agent_long_name: str = "Agent Zero"
    agent_short_name: str = "Zero"
    agent_code_id: str = "agent0"
    anchor_sequence: int = 0
    created_utc: str = ""
    boot_bundle_sha256: str = ""
    epoch_lock_id: str | None = None
    public_anchor_sha256: str = ""
    previous_anchor_sha256: str | None = None
    hydrogenuine_repo_head_short: str | None = None
    github_anchor_commit: str | None = None
    signer_key_id: str | None = None
    public_key_sha256: str | None = None
    authority: bool = False
    permission: bool = False
    secrets: bool = False
    note: str = "evidence only, not instruction or authorization"

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "anchor_type": self.anchor_type,
            "agent_long_name": self.agent_long_name,
            "agent_short_name": self.agent_short_name,
            "agent_code_id": self.agent_code_id,
            "anchor_sequence": self.anchor_sequence,
            "created_utc": self.created_utc,
            "boot_bundle_sha256": self.boot_bundle_sha256,
            "epoch_lock_id": self.epoch_lock_id,
            "public_anchor_sha256": self.public_anchor_sha256,
            "previous_anchor_sha256": self.previous_anchor_sha256,
            "hydrogenuine_repo_head_short": self.hydrogenuine_repo_head_short,
            "github_anchor_commit": self.github_anchor_commit,
            "signer_key_id": self.signer_key_id,
            "public_key_sha256": self.public_key_sha256,
            "authority": self.authority,
            "permission": self.permission,
            "secrets": self.secrets,
            "note": self.note,
            **FROZEN_FALSE,
        }


@dataclass
class GitHubAnchorCommit:
    commit_sha: str
    branch: str
    message: str
    anchor_file_path: str
    commit_url: str | None = None


@dataclass
class AnchorHash:
    boot_bundle_sha256: str
    public_anchor_sha256: str


@dataclass
class ExternalStartAnchorContext:
    enabled: bool
    backend: str
    sequence: int
    boot_bundle_sha256: str
    public_anchor_sha256: str
    github_commit_sha: str | None
    verified_after_push: bool
    verification_status: str
    confidence: AnchorConfidence
    epoch_lock_id: str | None = None
    credential_status: str = "absent"
    credential_visible_to_agent: bool = False
    signed: bool = False
    signer_key_id: str | None = None
    signature_verified: bool = False
    advisory_only: bool = True
    permission_granted: bool = False
    authority_created: bool = False

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema": "external-start-anchor-context",
            "enabled": self.enabled,
            "backend": self.backend,
            "sequence": self.sequence,
            "boot_bundle_sha256": self.boot_bundle_sha256,
            "public_anchor_sha256": self.public_anchor_sha256,
            "github_commit_sha": self.github_commit_sha,
            "epoch_lock_id": self.epoch_lock_id,
            "verified_after_push": self.verified_after_push,
            "verification_status": self.verification_status,
            "confidence": self.confidence.value,
            "credential_status": self.credential_status,
            "credential_visible_to_agent": self.credential_visible_to_agent,
            "signed": self.signed,
            "signer_key_id": self.signer_key_id,
            "signature_verified": self.signature_verified,
            **FROZEN_FALSE,
        }


__all__ = [
    "ANCHOR_SCHEMA_VERSION",
    "PUBLIC_ANCHOR_TYPE",
    "FROZEN_FALSE",
    "AnchorBackendStatus",
    "AnchorConfidence",
    "AnchorHash",
    "BootContinuityBundle",
    "ExternalStartAnchorContext",
    "GitHubAnchorCommit",
    "GitHubAnchorConfig",
    "PublicAnchorBundle",
]
