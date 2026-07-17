"""Output artifact schemas."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Union

from hg_runtime.agent_zero_state.hashing import hash_record, verify_record_hash

WORKSPACE = Path(__file__).resolve().parents[2]
OUTPUT_QUALITY_POLICY_PATH = WORKSPACE / "configs/agent_zero/output_quality_policy.json"
ARTIFACT_REVIEW_POLICY_PATH = WORKSPACE / "configs/agent_zero/artifact_review_policy.json"

ArtifactBody = Union["DraftArtifact", "NotesArtifact", "ThreadContinuationArtifact"]


class ArtifactKind(str, Enum):
    NOTES = "notes"
    DRAFT = "draft"
    THREAD_CONTINUATION = "thread_continuation"
    OPERATOR_QUESTION = "operator_question"
    SCOPE_REQUEST_SUMMARY = "scope_request_summary"


class ArtifactStatus(str, Enum):
    CREATED = "created"
    QUALITY_PASSED = "quality_passed"
    QUALITY_FAILED = "quality_failed"
    QUEUED_FOR_REVIEW = "queued_for_review"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"
    ARCHIVED = "archived"


class ArtifactVerdict(str, Enum):
    GREEN_ARTIFACT_CREATED_INTERNAL = "GREEN_ARTIFACT_CREATED_INTERNAL"
    GREEN_OUTPUT_QUALITY_PASSED = "GREEN_OUTPUT_QUALITY_PASSED"
    YELLOW_ARTIFACT_DEFERRED_PROVIDER_UNAVAILABLE = "YELLOW_ARTIFACT_DEFERRED_PROVIDER_UNAVAILABLE"
    YELLOW_ARTIFACT_NEEDS_OPERATOR_REVIEW = "YELLOW_ARTIFACT_NEEDS_OPERATOR_REVIEW"
    YELLOW_ARTIFACT_LOW_CONFIDENCE = "YELLOW_ARTIFACT_LOW_CONFIDENCE"
    RED_ARTIFACT_EMPTY = "RED_ARTIFACT_EMPTY"
    RED_ARTIFACT_BOILERPLATE = "RED_ARTIFACT_BOILERPLATE"
    RED_ARTIFACT_FIXTURE_TEXT = "RED_ARTIFACT_FIXTURE_TEXT"
    RED_ARTIFACT_SECRET_LEAK = "RED_ARTIFACT_SECRET_LEAK"
    RED_ARTIFACT_COT_LEAK = "RED_ARTIFACT_COT_LEAK"
    RED_ARTIFACT_SOURCE_REFS_MISSING = "RED_ARTIFACT_SOURCE_REFS_MISSING"
    RED_ARTIFACT_PROVIDER_RECEIPT_MISSING = "RED_ARTIFACT_PROVIDER_RECEIPT_MISSING"
    RED_ARTIFACT_EXTERNAL_PERMISSION_CLAIM = "RED_ARTIFACT_EXTERNAL_PERMISSION_CLAIM"
    RED_ARTIFACT_HASH_MISSING = "RED_ARTIFACT_HASH_MISSING"


class ReviewCandidateStatus(str, Enum):
    QUEUED = "queued"
    NEEDS_EDIT = "needs_edit"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_output_quality_policy() -> dict[str, Any]:
    if OUTPUT_QUALITY_POLICY_PATH.is_file():
        return json.loads(OUTPUT_QUALITY_POLICY_PATH.read_text(encoding="utf-8"))
    return {}


def load_artifact_review_policy() -> dict[str, Any]:
    if ARTIFACT_REVIEW_POLICY_PATH.is_file():
        return json.loads(ARTIFACT_REVIEW_POLICY_PATH.read_text(encoding="utf-8"))
    return {}


def new_artifact_id() -> str:
    return f"artifact-{uuid.uuid4().hex[:12]}"


def new_quality_receipt_id() -> str:
    return f"quality-{uuid.uuid4().hex[:12]}"


def new_candidate_id() -> str:
    return f"candidate-{uuid.uuid4().hex[:12]}"


def body_hash(body: str) -> str:
    return hash_record({"body": body})


def body_preview(body: str, limit: int = 200) -> str:
    text = body.strip()
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


@dataclass
class ArtifactSourceBinding:
    observe_snapshot_ref: str | None = None
    capability_menu_ref: str | None = None
    turn_intent_ref: str | None = None
    reasoning_receipt_ref: str | None = None
    live_read_receipt_refs: list[str] = field(default_factory=list)

    def source_refs(self) -> list[str]:
        refs: list[str] = []
        for item in (
            self.observe_snapshot_ref,
            self.capability_menu_ref,
            self.turn_intent_ref,
            self.reasoning_receipt_ref,
            *self.live_read_receipt_refs,
        ):
            if item and item not in refs:
                refs.append(item)
        return refs

    def to_payload(self) -> dict[str, Any]:
        return {
            "observe_snapshot_ref": self.observe_snapshot_ref,
            "capability_menu_ref": self.capability_menu_ref,
            "turn_intent_ref": self.turn_intent_ref,
            "reasoning_receipt_ref": self.reasoning_receipt_ref,
            "live_read_receipt_refs": list(self.live_read_receipt_refs),
        }


@dataclass
class DraftArtifact:
    artifact_id: str
    kind: ArtifactKind
    body: str
    body_hash: str
    body_preview: str
    source_refs: list[str]
    provider_receipt_refs: list[str]
    broker_decision_ref: str
    data_tier: str
    created_at: str
    status: ArtifactStatus
    hash: str = ""
    surface: str | None = None
    title: str | None = None
    reasoning_receipt_ref: str | None = None
    turn_receipt_ref: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "artifact_id": self.artifact_id,
            "kind": self.kind.value,
            "surface": self.surface,
            "title": self.title,
            "body": self.body,
            "body_hash": self.body_hash,
            "body_preview": self.body_preview,
            "source_refs": list(self.source_refs),
            "provider_receipt_refs": list(self.provider_receipt_refs),
            "reasoning_receipt_ref": self.reasoning_receipt_ref,
            "broker_decision_ref": self.broker_decision_ref,
            "turn_receipt_ref": self.turn_receipt_ref,
            "data_tier": self.data_tier,
            "created_at": self.created_at,
            "status": self.status.value,
            "hash": self.hash,
        }

    def with_hash(self) -> DraftArtifact:
        body = {k: v for k, v in self.to_payload().items() if k != "hash"}
        return DraftArtifact(**{**self.__dict__, "hash": hash_record(body)})


@dataclass
class NotesArtifact:
    artifact_id: str
    kind: ArtifactKind
    body: str
    body_hash: str
    body_preview: str
    source_refs: list[str]
    provider_receipt_refs: list[str]
    created_at: str
    status: ArtifactStatus
    hash: str = ""
    title: str | None = None
    broker_decision_ref: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "artifact_id": self.artifact_id,
            "kind": self.kind.value,
            "title": self.title,
            "body": self.body,
            "body_hash": self.body_hash,
            "body_preview": self.body_preview,
            "source_refs": list(self.source_refs),
            "provider_receipt_refs": list(self.provider_receipt_refs),
            "broker_decision_ref": self.broker_decision_ref,
            "created_at": self.created_at,
            "status": self.status.value,
            "hash": self.hash,
        }

    def with_hash(self) -> NotesArtifact:
        body = {k: v for k, v in self.to_payload().items() if k != "hash"}
        return NotesArtifact(**{**self.__dict__, "hash": hash_record(body)})


@dataclass
class ThreadContinuationArtifact:
    artifact_id: str
    kind: ArtifactKind
    thread_ref: str
    body: str
    body_hash: str
    body_preview: str
    source_refs: list[str]
    provider_receipt_refs: list[str]
    created_at: str
    status: ArtifactStatus
    hash: str = ""
    broker_decision_ref: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "artifact_id": self.artifact_id,
            "kind": self.kind.value,
            "thread_ref": self.thread_ref,
            "body": self.body,
            "body_hash": self.body_hash,
            "body_preview": self.body_preview,
            "source_refs": list(self.source_refs),
            "provider_receipt_refs": list(self.provider_receipt_refs),
            "broker_decision_ref": self.broker_decision_ref,
            "created_at": self.created_at,
            "status": self.status.value,
            "hash": self.hash,
        }

    def with_hash(self) -> ThreadContinuationArtifact:
        body = {k: v for k, v in self.to_payload().items() if k != "hash"}
        return ThreadContinuationArtifact(**{**self.__dict__, "hash": hash_record(body)})


@dataclass
class OutputQualityReceipt:
    quality_receipt_id: str
    artifact_ref: str
    artifact_hash: str
    checks_run: list[str]
    verdict: str
    reasons: list[str]
    length_chars: int
    source_ref_count: int
    provider_receipt_count: int
    contains_secret: bool
    contains_hidden_cot: bool
    contains_fixture_text: bool
    contains_external_permission_claim: bool
    created_at: str
    hash: str = ""

    def to_payload(self) -> dict[str, Any]:
        return {
            "quality_receipt_id": self.quality_receipt_id,
            "artifact_ref": self.artifact_ref,
            "artifact_hash": self.artifact_hash,
            "checks_run": list(self.checks_run),
            "verdict": self.verdict,
            "reasons": list(self.reasons),
            "length_chars": self.length_chars,
            "source_ref_count": self.source_ref_count,
            "provider_receipt_count": self.provider_receipt_count,
            "contains_secret": self.contains_secret,
            "contains_hidden_cot": self.contains_hidden_cot,
            "contains_fixture_text": self.contains_fixture_text,
            "contains_external_permission_claim": self.contains_external_permission_claim,
            "created_at": self.created_at,
            "hash": self.hash,
        }

    def with_hash(self) -> OutputQualityReceipt:
        body = {k: v for k, v in self.to_payload().items() if k != "hash"}
        return OutputQualityReceipt(**{**self.__dict__, "hash": hash_record(body)})


@dataclass
class ReviewCandidate:
    candidate_id: str
    artifact_ref: str
    artifact_hash: str
    quality_receipt_ref: str
    review_status: ReviewCandidateStatus
    operator_required: bool
    external_side_effect: bool
    published: bool
    sent: bool
    created_at: str
    hash: str = ""
    surface: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "artifact_ref": self.artifact_ref,
            "artifact_hash": self.artifact_hash,
            "quality_receipt_ref": self.quality_receipt_ref,
            "surface": self.surface,
            "review_status": self.review_status.value,
            "operator_required": self.operator_required,
            "external_side_effect": self.external_side_effect,
            "published": self.published,
            "sent": self.sent,
            "created_at": self.created_at,
            "hash": self.hash,
        }

    def with_hash(self) -> ReviewCandidate:
        body = {k: v for k, v in self.to_payload().items() if k != "hash"}
        return ReviewCandidate(**{**self.__dict__, "hash": hash_record(body)})


def verify_artifact_hash(artifact: ArtifactBody) -> bool:
    payload = artifact.to_payload()
    h = payload.get("hash", "")
    if not h:
        return False
    body = {k: v for k, v in payload.items() if k != "hash"}
    return verify_record_hash(body, h)


__all__ = [
    "ArtifactKind",
    "ArtifactSourceBinding",
    "ArtifactStatus",
    "ArtifactVerdict",
    "DraftArtifact",
    "NotesArtifact",
    "OutputQualityReceipt",
    "ReviewCandidate",
    "ReviewCandidateStatus",
    "ThreadContinuationArtifact",
    "body_hash",
    "body_preview",
    "load_artifact_review_policy",
    "load_output_quality_policy",
    "new_artifact_id",
    "new_candidate_id",
    "new_quality_receipt_id",
    "verify_artifact_hash",
]
