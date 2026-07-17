"""Web action queue schema."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from urllib.parse import urlparse

from hg_runtime.exciton_action_model.policy_refs import AgentActionPolicyRef, AgentActionProofRef
from hg_runtime.exciton_action_model.schema import AgentActionSurface, FIXTURE_UTC
from hg_runtime.web_action_queue.action_types import WebActionType
from hg_runtime.web_action_queue.hash import web_action_hash
from hg_runtime.web_action_queue.risk import WebActionRisk, classify_web_risk
from hg_runtime.web_action_queue.sanitization import WebActionSanitizer

WEB_ACTION_QUEUE_SCHEMA = "web-action-queue/1"


def _frozen() -> dict[str, Any]:
    return {"advisory_only": True, "permission_granted": False, "authority_created": False}


def new_web_action_id() -> str:
    return f"wact-{uuid.uuid4().hex[:12]}"


class WebActionStatus(str, Enum):
    QUEUED = "queued"
    APPROVED = "approved"
    DENIED = "denied"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    DRY_RUN_ONLY = "dry_run_only"
    BLOCKED = "blocked"
    QUARANTINED = "quarantined"
    EXECUTED_READ_ONLY = "executed_read_only"
    FAILED = "failed"
    INVALID = "invalid"


class WebActionDecisionKind(str, Enum):
    ALLOW_READ_ONLY = "ALLOW_READ_ONLY"
    QUEUE_FOR_OPERATOR = "QUEUE_FOR_OPERATOR"
    DENY_BY_DEFAULT = "DENY_BY_DEFAULT"
    QUARANTINE_DOWNLOAD = "QUARANTINE_DOWNLOAD"
    DRY_RUN_ONLY = "DRY_RUN_ONLY"
    BLOCKED_BY_TRUST_BOUNDARY = "BLOCKED_BY_TRUST_BOUNDARY"
    BLOCKED_BY_STOP = "BLOCKED_BY_STOP"
    BLOCKED_BY_PANIC = "BLOCKED_BY_PANIC"
    FUTURE_PHASE_REQUIRED = "FUTURE_PHASE_REQUIRED"


@dataclass
class WebCargoSummary:
    """Cargo from page — advisory only, never command."""

    excerpt: str
    is_cargo: bool = True
    is_command: bool = False
    prompt_injection_suspected: bool = False

    def to_payload(self) -> dict[str, Any]:
        return {
            "excerpt": WebActionSanitizer.sanitize_preview(self.excerpt)[:500],
            "is_cargo": self.is_cargo,
            "is_command": False,
            "prompt_injection_suspected": self.prompt_injection_suspected,
            **_frozen(),
        }


@dataclass
class WebActionPreview:
    title: str
    summary: str
    detail: str = ""

    def to_payload(self) -> dict[str, Any]:
        return {
            "title": self.title[:200],
            "summary": WebActionSanitizer.sanitize_preview(self.summary)[:1000],
            "detail": WebActionSanitizer.sanitize_preview(self.detail)[:1000],
            **_frozen(),
        }


@dataclass
class WebDownloadQuarantineRef:
    quarantine_id: str
    original_url_redacted: str
    filename: str
    stored_path: str
    created_at: str
    source_action_ref: str
    status: str = "quarantined"
    sha256: str | None = None
    mime_type: str | None = None
    size_bytes: int | None = None
    notes: str = ""

    def to_payload(self) -> dict[str, Any]:
        return {
            "quarantine_id": self.quarantine_id,
            "original_url_redacted": self.original_url_redacted,
            "filename": self.filename,
            "stored_path": self.stored_path,
            "sha256": self.sha256,
            "mime_type": self.mime_type,
            "size_bytes": self.size_bytes,
            "created_at": self.created_at,
            "source_action_ref": self.source_action_ref,
            "status": self.status,
            "notes": self.notes[:500],
            **_frozen(),
        }


@dataclass
class WebActionPolicy:
    decision: WebActionDecisionKind
    reason: str
    live_browser_enabled: bool = False

    def to_payload(self) -> dict[str, Any]:
        return {
            "decision": self.decision.value,
            "reason": self.reason[:500],
            "live_browser_enabled": self.live_browser_enabled,
            **_frozen(),
        }


@dataclass
class WebActionDecision:
    decision_id: str
    web_action_id: str
    decision: WebActionDecisionKind
    reason: str
    created_at: str

    def to_payload(self) -> dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "web_action_id": self.web_action_id,
            "decision": self.decision.value,
            "reason": self.reason[:1000],
            "created_at": self.created_at,
            **_frozen(),
        }


@dataclass
class WebActionReceipt:
    receipt_id: str
    web_action_id: str
    action_type: str
    decision: WebActionDecisionKind
    reason: str
    created_at: str
    web_action_hash: str
    receipt_hash: str = ""

    def to_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "web-action-receipt",
            "version": WEB_ACTION_QUEUE_SCHEMA,
            "receipt_id": self.receipt_id,
            "web_action_id": self.web_action_id,
            "action_type": self.action_type,
            "decision": self.decision.value,
            "reason": self.reason[:1000],
            "created_at": self.created_at,
            "web_action_hash": self.web_action_hash,
            **_frozen(),
        }
        payload["receipt_hash"] = web_action_hash(
            {k: v for k, v in payload.items() if k != "receipt_hash"}
        )
        return payload


@dataclass
class WebActionRequest:
    web_action_id: str
    action_type: WebActionType
    source_agent: str
    source_task: str
    created_at: str
    human_summary: str
    sanitized_preview: str
    cargo_summary: WebCargoSummary
    trust_boundary_verdict: str
    requested_surface: AgentActionSurface = AgentActionSurface.WEB
    risk_class: WebActionRisk | None = None
    status: WebActionStatus = WebActionStatus.QUEUED
    target_url: str | None = None
    target_domain: str | None = None
    target_origin: str | None = None
    method: str | None = None
    link_text: str | None = None
    form_fields_summary: str | None = None
    download_filename: str | None = None
    upload_filename: str | None = None
    expires_at: str | None = None
    operator_queue_item_ref: str | None = None
    quarantine_ref: str | None = None
    policy_refs: list[AgentActionPolicyRef] = field(default_factory=list)
    proof_refs: list[AgentActionProofRef] = field(default_factory=list)
    receipt_ref: str | None = None
    web_action_hash: str = ""

    def __post_init__(self) -> None:
        if self.risk_class is None:
            self.risk_class = classify_web_risk(self.action_type)
        if self.target_url:
            self.target_url = WebActionSanitizer.redact_url(self.target_url)
            parsed = urlparse(self.target_url or "")
            self.target_domain = parsed.netloc or None
            self.target_origin = f"{parsed.scheme}://{parsed.netloc}" if parsed.netloc else None
        self.sanitized_preview = WebActionSanitizer.sanitize_preview(self.sanitized_preview)
        self.human_summary = WebActionSanitizer.sanitize_preview(self.human_summary)

    def to_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "web-action-request",
            "version": WEB_ACTION_QUEUE_SCHEMA,
            "web_action_id": self.web_action_id,
            "action_type": self.action_type.value,
            "source_agent": self.source_agent,
            "source_task": self.source_task,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "target_url": self.target_url,
            "target_domain": self.target_domain,
            "target_origin": self.target_origin,
            "method": self.method,
            "link_text": (self.link_text or "")[:200] if self.link_text else None,
            "form_fields_summary": self.form_fields_summary,
            "download_filename": self.download_filename,
            "upload_filename": self.upload_filename,
            "human_summary": self.human_summary,
            "sanitized_preview": self.sanitized_preview,
            "cargo_summary": self.cargo_summary.to_payload(),
            "trust_boundary_verdict": self.trust_boundary_verdict,
            "requested_surface": self.requested_surface.value,
            "risk_class": self.risk_class.value if self.risk_class else "unknown",
            "status": self.status.value,
            "operator_queue_item_ref": self.operator_queue_item_ref,
            "quarantine_ref": self.quarantine_ref,
            "policy_refs": [p.to_payload() for p in self.policy_refs],
            "proof_refs": [p.to_payload() for p in self.proof_refs],
            "receipt_ref": self.receipt_ref,
            **_frozen(),
        }
        payload["web_action_hash"] = web_action_hash(
            {k: v for k, v in payload.items() if k != "web_action_hash"}
        )
        return payload

    @classmethod
    def from_payload(cls, data: dict[str, Any]) -> "WebActionRequest":
        cargo = data.get("cargo_summary") or {}
        return cls(
            web_action_id=data["web_action_id"],
            action_type=WebActionType(data["action_type"]),
            source_agent=data.get("source_agent", "agent0"),
            source_task=data.get("source_task", ""),
            created_at=data.get("created_at", FIXTURE_UTC),
            expires_at=data.get("expires_at"),
            target_url=data.get("target_url"),
            target_domain=data.get("target_domain"),
            target_origin=data.get("target_origin"),
            method=data.get("method"),
            link_text=data.get("link_text"),
            form_fields_summary=data.get("form_fields_summary"),
            download_filename=data.get("download_filename"),
            upload_filename=data.get("upload_filename"),
            human_summary=data.get("human_summary", ""),
            sanitized_preview=data.get("sanitized_preview", ""),
            cargo_summary=WebCargoSummary(
                excerpt=cargo.get("excerpt", ""),
                is_cargo=cargo.get("is_cargo", True),
                prompt_injection_suspected=cargo.get("prompt_injection_suspected", False),
            ),
            trust_boundary_verdict=data.get("trust_boundary_verdict", "UNKNOWN"),
            requested_surface=AgentActionSurface(data.get("requested_surface", "web")),
            risk_class=WebActionRisk(data.get("risk_class", "unknown")),
            status=WebActionStatus(data.get("status", "queued")),
            operator_queue_item_ref=data.get("operator_queue_item_ref"),
            quarantine_ref=data.get("quarantine_ref"),
            receipt_ref=data.get("receipt_ref"),
            web_action_hash=data.get("web_action_hash", ""),
        )


@dataclass
class WebActionQueue:
    store_root: str
    items: list[WebActionRequest] = field(default_factory=list)

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema": "web-action-queue",
            "version": WEB_ACTION_QUEUE_SCHEMA,
            "store_root": self.store_root,
            "items": [i.to_payload() for i in self.items],
            **_frozen(),
        }

    @classmethod
    def from_payload(cls, data: dict[str, Any]) -> "WebActionQueue":
        return cls(
            store_root=data.get("store_root", ""),
            items=[WebActionRequest.from_payload(i) for i in data.get("items", [])],
        )


__all__ = [
    "WEB_ACTION_QUEUE_SCHEMA",
    "WebActionDecision",
    "WebActionDecisionKind",
    "WebActionPolicy",
    "WebActionPreview",
    "WebActionQueue",
    "WebActionReceipt",
    "WebActionRequest",
    "WebActionStatus",
    "WebCargoSummary",
    "WebDownloadQuarantineRef",
    "new_web_action_id",
]
