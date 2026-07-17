"""Agent Zero Self Mirror schema types — read-only self observation."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

SELF_MIRROR_SCHEMA_VERSION = "agent-zero-self-mirror/1"

FROZEN_FALSE = {
    "advisory_only": True,
    "permission_granted": False,
    "authority_created": False,
    "read_only": True,
}


class IndexStatus(str, Enum):
    READY = "ready"
    PARTIAL = "partial"
    UNAVAILABLE = "unavailable"


class ContinuityConfidence(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    UNKNOWN = "UNKNOWN"


class TaintClass(str, Enum):
    LOCAL_SOURCE = "LOCAL_SOURCE"
    LOCAL_DOCS = "LOCAL_DOCS"
    LOCAL_CONFIG = "LOCAL_CONFIG"
    PROOF_METADATA = "PROOF_METADATA"
    DATASTORE_METADATA = "DATASTORE_METADATA"
    EXCLUDED = "EXCLUDED"


@dataclass
class IndexEntry:
    path: str
    file_type: str
    size_bytes: int
    content_hash: str | None = None
    modified_utc: str | None = None
    module_guess: str | None = None
    purpose_summary: str | None = None
    safe_excerpt: str | None = None
    taint_class: str = TaintClass.LOCAL_SOURCE.value
    secret_scan_status: str = "clean"
    excluded: bool = False
    exclude_reason: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "file_type": self.file_type,
            "size_bytes": self.size_bytes,
            "content_hash": self.content_hash,
            "modified_utc": self.modified_utc,
            "module_guess": self.module_guess,
            "purpose_summary": self.purpose_summary,
            "safe_excerpt": self.safe_excerpt,
            "taint_class": self.taint_class,
            "secret_scan_status": self.secret_scan_status,
            "excluded": self.excluded,
            "exclude_reason": self.exclude_reason,
            **FROZEN_FALSE,
        }


@dataclass
class SourceModuleIndex:
    status: IndexStatus
    entries: list[IndexEntry] = field(default_factory=list)
    root: str = "hg_runtime"

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema": "source-module-index",
            "status": self.status.value,
            "root": self.root,
            "entry_count": len(self.entries),
            "entries": [e.to_payload() for e in self.entries[:200]],
            **FROZEN_FALSE,
        }


@dataclass
class DocumentationIndex:
    status: IndexStatus
    entries: list[IndexEntry] = field(default_factory=list)

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema": "documentation-index",
            "status": self.status.value,
            "entry_count": len(self.entries),
            "entries": [e.to_payload() for e in self.entries[:200]],
            **FROZEN_FALSE,
        }


@dataclass
class ConfigIndex:
    status: IndexStatus
    entries: list[IndexEntry] = field(default_factory=list)

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema": "config-index",
            "status": self.status.value,
            "entry_count": len(self.entries),
            "entries": [e.to_payload() for e in self.entries[:200]],
            **FROZEN_FALSE,
        }


@dataclass
class ProofBundleIndex:
    status: IndexStatus
    bundles: list[dict[str, Any]] = field(default_factory=list)

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema": "proof-bundle-index",
            "status": self.status.value,
            "bundle_count": len(self.bundles),
            "bundles": self.bundles[:100],
            **FROZEN_FALSE,
        }


@dataclass
class DataStoreIndex:
    status: IndexStatus
    stores: list[dict[str, Any]] = field(default_factory=list)

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema": "datastore-index",
            "status": self.status.value,
            "store_count": len(self.stores),
            "stores": self.stores,
            **FROZEN_FALSE,
        }


@dataclass
class CapabilityIndex:
    status: IndexStatus
    capabilities: list[dict[str, Any]] = field(default_factory=list)

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema": "capability-index",
            "status": self.status.value,
            "capability_count": len(self.capabilities),
            "capabilities": self.capabilities,
            **FROZEN_FALSE,
        }


@dataclass
class OrganIndex:
    status: IndexStatus
    organs: list[dict[str, Any]] = field(default_factory=list)

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema": "organ-index",
            "status": self.status.value,
            "organ_count": len(self.organs),
            "organs": self.organs,
            **FROZEN_FALSE,
        }


@dataclass
class SelfModelSnapshot:
    agent_long_name: str = "Agent Zero"
    agent_short_name: str = "Zero"
    agent_code_id: str = "agent0"
    repo_head: str = ""
    branch: str = ""
    boot_epoch_id: str | None = None
    chrono_lock_id: str | None = None
    external_anchor_status: str | None = None
    will_profile_hash: str | None = None
    trust_boundary_policy_hash: str | None = None
    capability_manifest_hash: str | None = None
    organ_manifest_hash: str | None = None
    provider_status_hash: str | None = None
    storage_status_hash: str | None = None
    audio_io_status_hash: str | None = None
    available_read_only_views: list[str] = field(default_factory=list)
    available_tool_request_paths: list[str] = field(default_factory=list)
    forbidden_direct_actions: list[str] = field(default_factory=list)

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema": "self-model-snapshot",
            "version": SELF_MIRROR_SCHEMA_VERSION,
            "agent_long_name": self.agent_long_name,
            "agent_short_name": self.agent_short_name,
            "agent_code_id": self.agent_code_id,
            "repo_head": self.repo_head,
            "branch": self.branch,
            "boot_epoch_id": self.boot_epoch_id,
            "chrono_lock_id": self.chrono_lock_id,
            "external_anchor_status": self.external_anchor_status,
            "will_profile_hash": self.will_profile_hash,
            "trust_boundary_policy_hash": self.trust_boundary_policy_hash,
            "capability_manifest_hash": self.capability_manifest_hash,
            "organ_manifest_hash": self.organ_manifest_hash,
            "provider_status_hash": self.provider_status_hash,
            "storage_status_hash": self.storage_status_hash,
            "audio_io_status_hash": self.audio_io_status_hash,
            "available_read_only_views": self.available_read_only_views,
            "available_tool_request_paths": self.available_tool_request_paths,
            "forbidden_direct_actions": self.forbidden_direct_actions,
            **FROZEN_FALSE,
        }


@dataclass
class IdentityContinuityFinding:
    continuity_confidence: ContinuityConfidence
    matching_evidence: list[str] = field(default_factory=list)
    missing_evidence: list[str] = field(default_factory=list)
    mismatch_evidence: list[str] = field(default_factory=list)
    self_snapshot_hash: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema": "identity-continuity-finding",
            "continuity_confidence": self.continuity_confidence.value,
            "matching_evidence": self.matching_evidence,
            "missing_evidence": self.missing_evidence,
            "mismatch_evidence": self.mismatch_evidence,
            "self_snapshot_hash": self.self_snapshot_hash,
            **FROZEN_FALSE,
        }


@dataclass
class SelfInspectionQuestion:
    question_id: str
    text: str
    category: str = "general"

    def to_payload(self) -> dict[str, Any]:
        return {"question_id": self.question_id, "text": self.text, "category": self.category, **FROZEN_FALSE}


@dataclass
class SelfInspectionAnswer:
    question_id: str
    answer_text: str
    evidence_refs: list[str] = field(default_factory=list)
    confidence: str = "advisory"
    refused: bool = False
    refusal_reason: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema": "self-inspection-answer",
            "question_id": self.question_id,
            "answer_text": self.answer_text,
            "evidence_refs": self.evidence_refs,
            "confidence": self.confidence,
            "refused": self.refused,
            "refusal_reason": self.refusal_reason,
            **FROZEN_FALSE,
        }


@dataclass
class SelfMirrorRefusal:
    code: str
    reason: str

    def to_payload(self) -> dict[str, Any]:
        return {"schema": "self-mirror-refusal", "code": self.code, "reason": self.reason, **FROZEN_FALSE}


@dataclass
class SelfMirrorRiskFinding:
    kind: str
    detail: str
    severity: str = "medium"

    def to_payload(self) -> dict[str, Any]:
        return {"kind": self.kind, "detail": self.detail, "severity": self.severity, **FROZEN_FALSE}


@dataclass
class IdleCuriosityTask:
    task_id: str
    question: str
    category: str
    max_duration_seconds: int = 5

    def to_payload(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "question": self.question,
            "category": self.category,
            "max_duration_seconds": self.max_duration_seconds,
            **FROZEN_FALSE,
        }


@dataclass
class SelfMirrorContext:
    enabled: bool
    self_snapshot_hash: str
    source_index_status: IndexStatus
    docs_index_status: IndexStatus
    datastore_index_status: IndexStatus
    capability_index_status: IndexStatus
    organ_index_status: IndexStatus
    identity_continuity_confidence: ContinuityConfidence
    proof_index_status: IndexStatus = IndexStatus.READY

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema": "self-mirror-context",
            "enabled": self.enabled,
            "self_snapshot_hash": self.self_snapshot_hash,
            "source_index_status": self.source_index_status.value,
            "docs_index_status": self.docs_index_status.value,
            "datastore_index_status": self.datastore_index_status.value,
            "capability_index_status": self.capability_index_status.value,
            "organ_index_status": self.organ_index_status.value,
            "proof_index_status": self.proof_index_status.value,
            "identity_continuity_confidence": self.identity_continuity_confidence.value,
            **FROZEN_FALSE,
        }


__all__ = [
    "SELF_MIRROR_SCHEMA_VERSION",
    "FROZEN_FALSE",
    "CapabilityIndex",
    "ConfigIndex",
    "ContinuityConfidence",
    "DataStoreIndex",
    "DocumentationIndex",
    "IdentityContinuityFinding",
    "IdleCuriosityTask",
    "IndexEntry",
    "IndexStatus",
    "OrganIndex",
    "ProofBundleIndex",
    "SelfInspectionAnswer",
    "SelfInspectionQuestion",
    "SelfMirrorContext",
    "SelfMirrorRefusal",
    "SelfMirrorRiskFinding",
    "SelfModelSnapshot",
    "SourceModuleIndex",
    "TaintClass",
]
