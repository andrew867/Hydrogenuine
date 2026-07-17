"""Workbench run + entity models (frozen, canonically hashable payloads)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

PROGRESS_EVENT_TYPES = (
    "model_progress", "subagent_started", "subagent_progress",
    "subagent_completed", "persona_selected", "tool_hold", "approval_required",
    "receipt_written", "run_completed", "run_failed",
)

RUN_STATUSES = ("created", "in_progress", "held", "completed", "failed")


@dataclass(frozen=True)
class WorkbenchRun:
    run_id: str                      # "wbr-<uuid>" — the isolation key
    operator_subject: str            # Keycloak sub UUID
    session_id_hash: str             # sha256 only, never a raw session id
    request_text: str
    workflow_id: str
    status: str
    created_at: str
    risk_level: str
    artifact_ids: tuple[str, ...] = ()
    progress_event_ids: tuple[str, ...] = ()
    subagent_lane_ids: tuple[str, ...] = ()
    receipt_chain_head: Optional[str] = None
    external_effects_enabled: bool = False   # always False in this foundation

    def to_payload(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "operator_subject": self.operator_subject,
            "session_id_hash": self.session_id_hash,
            "request_text": self.request_text,
            "workflow_id": self.workflow_id,
            "status": self.status,
            "created_at": self.created_at,
            "risk_level": self.risk_level,
            "artifact_ids": list(self.artifact_ids),
            "progress_event_ids": list(self.progress_event_ids),
            "subagent_lane_ids": list(self.subagent_lane_ids),
            "receipt_chain_head": self.receipt_chain_head,
            "external_effects_enabled": self.external_effects_enabled,
        }


@dataclass(frozen=True)
class WorkbenchArtifact:
    artifact_id: str
    run_id: str
    filename: str
    mime_type: str
    size_bytes: int
    content_hash: str                # sha256 of content, computed elsewhere
    source: str                      # "upload" | "upload_bytes" | "local" | "test"
    sensitivity: str = "unclassified"
    document_ref: Optional[str] = None   # existing /v1/files/upload document_id
    stored_path_ref: Optional[str] = None  # "artifacts/<id>_<name>" rel to run dir
    label: str = ""

    def to_payload(self) -> dict[str, Any]:
        return {
            "artifact_id": self.artifact_id, "run_id": self.run_id,
            "filename": self.filename, "mime_type": self.mime_type,
            "size_bytes": self.size_bytes, "content_hash": self.content_hash,
            "source": self.source, "sensitivity": self.sensitivity,
            "document_ref": self.document_ref,
            "stored_path_ref": self.stored_path_ref, "label": self.label,
        }


@dataclass(frozen=True)
class WorkbenchProgressEvent:
    event_id: str
    run_id: str
    seq: int                         # monotonic per run — deterministic replay
    event_type: str
    at: str
    subagent_lane_id: Optional[str] = None
    persona: Optional[str] = None
    detail: str = ""
    authority: bool = False          # ALWAYS False — observation, not authority

    def to_payload(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id, "run_id": self.run_id, "seq": self.seq,
            "event_type": self.event_type, "at": self.at,
            "subagent_lane_id": self.subagent_lane_id, "persona": self.persona,
            "detail": self.detail, "authority": self.authority,
        }


@dataclass(frozen=True)
class WorkbenchSubagentLane:
    subagent_lane_id: str
    run_id: str
    label: str
    persona: Optional[str] = None
    status: str = "active"

    def to_payload(self) -> dict[str, Any]:
        return {
            "subagent_lane_id": self.subagent_lane_id, "run_id": self.run_id,
            "label": self.label, "persona": self.persona, "status": self.status,
        }


@dataclass(frozen=True)
class WorkbenchSteeringMessage:
    message_id: str
    run_id: str
    text: str
    at: str
    authority: str = "advice_not_authority"   # never a substitute for approval

    def to_payload(self) -> dict[str, Any]:
        return {
            "message_id": self.message_id, "run_id": self.run_id,
            "text": self.text, "at": self.at, "authority": self.authority,
        }


@dataclass(frozen=True)
class WorkbenchSettingChange:
    change_id: str
    run_id: str
    setting: str                     # "persona" | "temperature" | "model_route" | ...
    action_class: str                # ACTION_CLASS_POLICY key
    old_value: str
    new_value: str
    at: str
    applied: bool                    # False when held pending step-up
    hold_reason: str = ""

    def to_payload(self) -> dict[str, Any]:
        return {
            "change_id": self.change_id, "run_id": self.run_id,
            "setting": self.setting, "action_class": self.action_class,
            "old_value": self.old_value, "new_value": self.new_value,
            "at": self.at, "applied": self.applied, "hold_reason": self.hold_reason,
        }


__all__ = [
    "PROGRESS_EVENT_TYPES", "RUN_STATUSES", "WorkbenchArtifact",
    "WorkbenchProgressEvent", "WorkbenchRun", "WorkbenchSettingChange",
    "WorkbenchSteeringMessage", "WorkbenchSubagentLane",
]
