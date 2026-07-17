"""External Witness Journal schema types."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

JOURNAL_SCHEMA_VERSION = "external_witness_journal/1"
JOURNAL_TYPE = "HYDROGENUINE_AGENT_ZERO_WITNESS_JOURNAL_V1"

FROZEN_FALSE = {
    "advisory_only": True,
    "permission_granted": False,
    "authority_created": False,
}


class WitnessEventClass(str, Enum):
    BOOT_START = "BOOT_START"
    BOOT_VERIFIED = "BOOT_VERIFIED"
    FIRST_WAKE_START = "FIRST_WAKE_START"
    FIRST_WAKE_COMPLETE = "FIRST_WAKE_COMPLETE"
    MISSION_START = "MISSION_START"
    MISSION_COMPLETE = "MISSION_COMPLETE"
    WEATHER_VOICE_START = "WEATHER_VOICE_START"
    WEATHER_VOICE_COMPLETE = "WEATHER_VOICE_COMPLETE"
    SLEEP_START = "SLEEP_START"
    SLEEP_COMPLETE = "SLEEP_COMPLETE"
    CLEAN_STOP = "CLEAN_STOP"
    PANIC_ENTERED = "PANIC_ENTERED"
    PANIC_CLEARED = "PANIC_CLEARED"
    WAKE_REFRESH_START = "WAKE_REFRESH_START"
    WAKE_REFRESH_COMPLETE = "WAKE_REFRESH_COMPLETE"
    CONTINUITY_RECOVERY_START = "CONTINUITY_RECOVERY_START"
    CONTINUITY_RECOVERY_COMPLETE = "CONTINUITY_RECOVERY_COMPLETE"
    IMPORTANT_STATE_MARKER = "IMPORTANT_STATE_MARKER"
    INCIDENT_MARKER = "INCIDENT_MARKER"
    POLICY_EPOCH_MARKER = "POLICY_EPOCH_MARKER"
    RELEASE_MARKER = "RELEASE_MARKER"
    OPERATOR_MARKER = "OPERATOR_MARKER"


class WitnessImportanceClass(str, Enum):
    ROUTINE = "ROUTINE"
    IMPORTANT = "IMPORTANT"
    CRITICAL = "CRITICAL"
    INCIDENT = "INCIDENT"
    RELEASE = "RELEASE"
    OPERATOR_PINNED = "OPERATOR_PINNED"


class WitnessAppendDecision(str, Enum):
    ALLOW_LOCAL_ONLY = "ALLOW_LOCAL_ONLY"
    ALLOW_LIVE_PUSH = "ALLOW_LIVE_PUSH"
    QUEUE_FOR_OPERATOR = "QUEUE_FOR_OPERATOR"
    DENY = "DENY"
    FULL_STOP = "FULL_STOP"


class AnchorWriterRequestKind(str, Enum):
    ANCHOR_IMPORTANT_EVENT = "ANCHOR_IMPORTANT_EVENT"
    ANCHOR_MISSION_START = "ANCHOR_MISSION_START"
    ANCHOR_MISSION_COMPLETE = "ANCHOR_MISSION_COMPLETE"
    ANCHOR_SLEEP_START = "ANCHOR_SLEEP_START"
    ANCHOR_SLEEP_COMPLETE = "ANCHOR_SLEEP_COMPLETE"
    ANCHOR_CONTINUITY_RECOVERY = "ANCHOR_CONTINUITY_RECOVERY"
    OPERATOR_APPEND = "OPERATOR_APPEND"


FORBIDDEN_PUBLIC_FRAGMENTS = (
    ".env",
    "api_key",
    "secret",
    "token",
    "password",
    "cookie",
    "bearer",
    "authorization:",
    "private_key",
)


@dataclass
class WitnessJournalConfig:
    enabled: bool = True
    anchor_id: str = "github-primary-dev"
    agent_long_name: str = "Agent Zero"
    agent_short_name: str = "Zero"
    agent_code_id: str = "agent0"
    anchor_repo_path: str = "../hydrogenuine-agent-zero-anchor"
    anchor_repo_remote: str = ""
    anchor_branch: str = "main"
    journal_dir: str = "anchors/agent0_journal"
    events_dir: str = "anchors/agent0_journal/events"
    chain_file: str = "anchors/agent0_journal/chain.json"
    latest_file: str = "anchors/agent0_journal/latest.json"
    allow_push: bool = False
    allow_create_repo: bool = False
    require_clean_anchor_repo: bool = True
    fetch_after_push: bool = True
    secondary_anchor_enabled: bool = False
    secondary_anchor_backend: str = "private_server_future"
    max_important_per_hour: int = 12
    advisory_only: bool = True
    permission_granted: bool = False
    authority_created: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WitnessJournalConfig:
        cfg = cls()
        for key, value in data.items():
            if key.startswith("_"):
                continue
            if hasattr(cfg, key):
                setattr(cfg, key, value)
        cfg._apply_env()
        return cfg

    def _apply_env(self) -> None:
        if os.environ.get("HG_ANCHOR_GITHUB_REPO_PATH"):
            self.anchor_repo_path = os.environ["HG_ANCHOR_GITHUB_REPO_PATH"]
        if os.environ.get("HG_ANCHOR_GITHUB_REMOTE"):
            self.anchor_repo_remote = os.environ["HG_ANCHOR_GITHUB_REMOTE"]
        if os.environ.get("HG_ANCHOR_GITHUB_BRANCH"):
            self.anchor_branch = os.environ["HG_ANCHOR_GITHUB_BRANCH"]
        if os.environ.get("HG_ANCHOR_ALLOW_PUSH", "").strip().lower() in {"1", "true", "yes", "on"}:
            self.allow_push = True
        if os.environ.get("HG_ANCHOR_ALLOW_CREATE_REPO", "").strip().lower() in {"1", "true", "yes", "on"}:
            self.allow_create_repo = True
        if os.environ.get("HG_WITNESS_JOURNAL_LIVE_PUSH", "").strip().lower() in {"1", "true", "yes", "on"}:
            self.allow_push = True

    def resolved_repo_path(self, workspace: Path | None = None) -> Path:
        raw = Path(self.anchor_repo_path)
        if raw.is_absolute():
            return raw
        base = workspace or Path.cwd()
        return (base / raw).resolve()


@dataclass
class WitnessJournalBundle:
    schema_version: str = JOURNAL_SCHEMA_VERSION
    journal_type: str = JOURNAL_TYPE
    event_class: WitnessEventClass = WitnessEventClass.BOOT_START
    importance_class: WitnessImportanceClass = WitnessImportanceClass.ROUTINE
    event_sequence: int = 0
    agent_long_name: str = "Agent Zero"
    agent_short_name: str = "Zero"
    agent_code_id: str = "agent0"
    created_utc: str = ""
    epoch_id: str | None = None
    epoch_lock_id: str | None = None
    chrono_lock_id: str | None = None
    external_start_anchor_sha256: str | None = None
    previous_journal_event_sha256: str | None = None
    previous_github_commit_sha: str | None = None
    local_state_commitment_sha256: str = ""
    local_receipt_bundle_sha256: str | None = None
    proof_bundle_ref_hash: str | None = None
    mission_id: str | None = None
    run_id: str | None = None
    event_summary_public: str = ""
    event_facts_public: dict[str, Any] = field(default_factory=dict)
    journal_event_sha256: str = ""
    github_commit_sha: str | None = None
    secrets_included: bool = False
    raw_memory_included: bool = False
    raw_audio_included: bool = False
    raw_browser_content_included: bool = False
    authority: bool = False
    permission: bool = False
    advisory_only: bool = True
    permission_granted: bool = False
    authority_created: bool = False

    def to_dict(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema_version": self.schema_version,
            "journal_type": self.journal_type,
            "event_class": self.event_class.value if isinstance(self.event_class, WitnessEventClass) else self.event_class,
            "importance_class": (
                self.importance_class.value
                if isinstance(self.importance_class, WitnessImportanceClass)
                else self.importance_class
            ),
            "event_sequence": self.event_sequence,
            "agent_long_name": self.agent_long_name,
            "agent_short_name": self.agent_short_name,
            "agent_code_id": self.agent_code_id,
            "created_utc": self.created_utc,
            "epoch_id": self.epoch_id,
            "epoch_lock_id": self.epoch_lock_id,
            "chrono_lock_id": self.chrono_lock_id,
            "external_start_anchor_sha256": self.external_start_anchor_sha256,
            "previous_journal_event_sha256": self.previous_journal_event_sha256,
            "previous_github_commit_sha": self.previous_github_commit_sha,
            "local_state_commitment_sha256": self.local_state_commitment_sha256,
            "local_receipt_bundle_sha256": self.local_receipt_bundle_sha256,
            "proof_bundle_ref_hash": self.proof_bundle_ref_hash,
            "mission_id": self.mission_id,
            "run_id": self.run_id,
            "event_summary_public": self.event_summary_public,
            "event_facts_public": self.event_facts_public,
            "secrets_included": self.secrets_included,
            "raw_memory_included": self.raw_memory_included,
            "raw_audio_included": self.raw_audio_included,
            "raw_browser_content_included": self.raw_browser_content_included,
            "authority": self.authority,
            "permission": self.permission,
            **FROZEN_FALSE,
        }
        if include_hash and self.journal_event_sha256:
            payload["journal_event_sha256"] = self.journal_event_sha256
        if self.github_commit_sha:
            payload["github_commit_sha"] = self.github_commit_sha
        return payload


@dataclass
class WitnessHashChain:
    latest_event_sequence: int = -1
    latest_event_sha256: str | None = None
    latest_signature_sha256: str | None = None
    latest_signer_key_id: str | None = None
    latest_github_commit_sha: str | None = None
    event_count: int = 0
    chain_verified: bool = False
    generated_utc: str = ""
    advisory_only: bool = True
    authority: bool = False
    permission: bool = False
    permission_granted: bool = False
    authority_created: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "latest_event_sequence": self.latest_event_sequence,
            "latest_event_sha256": self.latest_event_sha256,
            "latest_signature_sha256": self.latest_signature_sha256,
            "latest_signer_key_id": self.latest_signer_key_id,
            "latest_github_commit_sha": self.latest_github_commit_sha,
            "event_count": self.event_count,
            "chain_verified": self.chain_verified,
            "generated_utc": self.generated_utc,
            "authority": self.authority,
            "permission": self.permission,
            **FROZEN_FALSE,
        }


@dataclass
class AnchorWriterRequest:
    kind: AnchorWriterRequestKind
    event_class: WitnessEventClass
    importance: WitnessImportanceClass
    summary: str
    facts: dict[str, Any] = field(default_factory=dict)
    operator_invoked: bool = False
    agent_requested: bool = False
    push_requested: bool = False
    epoch_lock_id: str | None = None
    epoch_id: str | None = None
    mission_id: str | None = None
    run_id: str | None = None
    proof_ref: str | None = None
    anchor_handoff: dict[str, Any] | None = None


@dataclass
class AnchorWriterDecision:
    decision: WitnessAppendDecision
    verdict: str
    reason: str
    allow_push: bool = False
    queue_path: str | None = None


@dataclass
class WitnessJournalVerification:
    ok: bool
    chain_verified: bool
    event_count: int
    latest_sequence: int
    latest_event_sha256: str | None
    failures: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema": "witness-journal-verification",
            "ok": self.ok,
            "chain_verified": self.chain_verified,
            "event_count": self.event_count,
            "latest_sequence": self.latest_sequence,
            "latest_event_sha256": self.latest_event_sha256,
            "failures": self.failures,
            "warnings": self.warnings,
            **FROZEN_FALSE,
        }


@dataclass
class AgentZeroWitnessJournalContext:
    enabled: bool
    latest_event_sequence: int
    latest_event_sha256: str | None
    latest_github_commit_sha: str | None
    chain_verified: bool
    live_push_enabled: bool
    secondary_anchor_status: str
    signed_chain: bool = False
    latest_signature_sha256: str | None = None
    missing_delta_count: int = 0
    continuity_confidence: str = "UNKNOWN"
    advisory_only: bool = True
    permission_granted: bool = False
    authority_created: bool = False

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema": "external-witness-journal-context",
            "enabled": self.enabled,
            "latest_event_sequence": self.latest_event_sequence,
            "latest_event_sha256": self.latest_event_sha256,
            "latest_github_commit_sha": self.latest_github_commit_sha,
            "chain_verified": self.chain_verified,
            "live_push_enabled": self.live_push_enabled,
            "secondary_anchor_status": self.secondary_anchor_status,
            "signed_chain": self.signed_chain,
            "latest_signature_sha256": self.latest_signature_sha256,
            "missing_delta_count": self.missing_delta_count,
            "continuity_confidence": self.continuity_confidence,
            **FROZEN_FALSE,
        }


__all__ = [
    "FORBIDDEN_PUBLIC_FRAGMENTS",
    "FROZEN_FALSE",
    "JOURNAL_SCHEMA_VERSION",
    "JOURNAL_TYPE",
    "AgentZeroWitnessJournalContext",
    "AnchorWriterDecision",
    "AnchorWriterRequest",
    "AnchorWriterRequestKind",
    "WitnessAppendDecision",
    "WitnessEventClass",
    "WitnessHashChain",
    "WitnessImportanceClass",
    "WitnessJournalBundle",
    "WitnessJournalConfig",
    "WitnessJournalVerification",
]
