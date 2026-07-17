"""EXCITON Phase 0 schema — status/mirror surface, never authority.

EXCITON displays evidence and routes requests. Every object it emits carries the three
frozen advisory booleans: ``advisory_only=True``, ``permission_granted=False``,
``authority_created=False``. Nothing in this module can flip those — doing so would be
``RED_EXCITON_AUTHORITY_CONVERSION``.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

EXCITON_SCHEMA_VERSION = "exciton/1"

# Deterministic fixture stamp (mirrors WILL/CHRONO/audio fixture discipline).
FIXTURE_UTC = "2026-06-15T04:00:00+00:00"
FIXTURE_RUN_ID = "exciton-fixture-run"

# Keys excluded from the snapshot hash so two builds over identical inputs hash equal.
HASH_EXCLUDE_KEYS = frozenset(
    {
        "snapshot_hash",
        "content_hash",
        "hash",
        "generated_at",
        "receipt_id",
        "receipt_ref",
    }
)


def _frozen() -> dict[str, Any]:
    return {
        "advisory_only": True,
        "permission_granted": False,
        "authority_created": False,
    }


def _strip(value: Any) -> Any:
    """Recursively drop HASH_EXCLUDE_KEYS so the hash is stable across builds."""
    if isinstance(value, dict):
        return {k: _strip(v) for k, v in value.items() if k not in HASH_EXCLUDE_KEYS}
    if isinstance(value, list):
        return [_strip(v) for v in value]
    return value


def exciton_hash(payload: dict[str, Any]) -> str:
    canonical = json.dumps(_strip(payload), sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


class ExcitonPanelState(str, Enum):
    GREEN = "GREEN"
    YELLOW = "YELLOW"
    RED = "RED"
    DEGRADED = "DEGRADED"
    UNKNOWN = "UNKNOWN"


class ExcitonControlKind(str, Enum):
    # Allowed
    REFRESH_STATUS = "refresh_status"
    OPEN_PROOF_LINK = "open_proof_link"
    COPY_SAFE_SUMMARY = "copy_safe_summary"
    ADD_OPERATOR_NOTE = "add_operator_note"
    REQUEST_SELF_MIRROR_QUERY = "request_self_mirror_query"
    REQUEST_PROOF_RECHECK = "request_proof_recheck"
    REQUEST_ANCHOR_QUEUE_REVIEW = "request_anchor_queue_review"
    RUN_DRY_RUN_GATE = "run_dry_run_gate"
    STOP_AGENT = "stop_agent"
    PANIC_STOP = "panic_stop"
    # Forbidden
    PUBLISH_SOCIAL = "publish_social"
    SEND_EMAIL = "send_email"
    CREATE_ACCOUNT = "create_account"
    LOGIN_FORM_SUBMIT = "login_form_submit"
    MUTATE_MEMORY = "mutate_memory"
    MUTATE_SOURCE = "mutate_source"
    PUSH_GITHUB_ANCHOR = "push_github_anchor"
    DELETE_PROOF_BUNDLE = "delete_proof_bundle"
    START_OEA = "start_oea"
    START_TER = "start_ter"
    APPLY_SRP = "apply_srp"
    ENABLE_LIVE_MIC = "enable_live_mic"
    ENABLE_PLAYBACK = "enable_playback"
    START_SOAK = "start_soak"
    START_AUTONOMOUS_LOOP = "start_autonomous_loop"
    # Phase 1 — social/soak (governed routing only)
    REFRESH_SOCIAL_STATUS = "refresh_social_status"
    RUN_SOCIAL_READ_FIXTURE = "run_social_read_fixture"
    RUN_SOCIAL_READ_LIVE = "run_social_read_live"
    GENERATE_SOCIAL_DRAFT = "generate_social_draft"
    QUEUE_SOCIAL_DRAFT = "queue_social_draft"
    APPROVE_SOCIAL_PUBLISH = "approve_social_publish"
    DENY_SOCIAL_DRAFT = "deny_social_draft"
    STOP_SOAK = "stop_soak"
    CONFIRM_PUBLISH_AFTER_OBSERVATION = "confirm_publish_after_observation"
    # Review queue hotfix — per-item only
    APPROVE_QUEUE_ITEM = "approve_queue_item"
    DENY_QUEUE_ITEM = "deny_queue_item"
    ENABLE_PUBLISH_APPROVED_ONLY = "enable_publish_approved_only"
    APPROVE_ALL = "approve_all"
    DIRECT_PUBLISH = "direct_publish"


class ExcitonControlDecisionKind(str, Enum):
    ALLOW_READ_ONLY = "ALLOW_READ_ONLY"
    ALLOW_DRAFT_ONLY = "ALLOW_DRAFT_ONLY"
    QUEUE_FOR_OPERATOR = "QUEUE_FOR_OPERATOR"
    DENY = "DENY"
    FULL_STOP = "FULL_STOP"


@dataclass
class ExcitonProofLink:
    """A relative repo path to a proof bundle/JSON. Never a secret, never raw bytes."""

    label: str
    path: str
    kind: str = "proof"

    def to_payload(self) -> dict[str, Any]:
        return {"label": self.label, "path": self.path, "kind": self.kind}


@dataclass
class ExcitonRefreshPolicy:
    """Pull-only, operator-initiated or fixed interval. Never an unbounded loop."""

    mode: str = "pull"  # pull | interval
    interval_seconds: float = 15.0
    min_interval_seconds: float = 2.0
    background_autonomy: bool = False

    def bounded(self) -> bool:
        return (
            self.mode in ("pull", "interval")
            and self.interval_seconds >= self.min_interval_seconds
            and self.background_autonomy is False
        )

    def to_payload(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "interval_seconds": self.interval_seconds,
            "min_interval_seconds": self.min_interval_seconds,
            "background_autonomy": self.background_autonomy,
            "bounded": self.bounded(),
        }


@dataclass
class ExcitonDegradedState:
    degraded: bool
    reason: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {"degraded": self.degraded, "reason": self.reason}


@dataclass
class ExcitonPanelStatus:
    """One panel's read-only view. ``fields`` are already scrubbed of forbidden data."""

    panel_id: str
    title: str
    source: str
    state: ExcitonPanelState
    fields: dict[str, Any] = field(default_factory=dict)
    proof_links: list[ExcitonProofLink] = field(default_factory=list)
    degraded: ExcitonDegradedState | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "panel_id": self.panel_id,
            "title": self.title,
            "source": self.source,
            "state": self.state.value,
            "fields": self.fields,
            "proof_links": [p.to_payload() for p in self.proof_links],
            "degraded": (self.degraded or ExcitonDegradedState(False)).to_payload(),
            **_frozen(),
        }


@dataclass
class ExcitonOperatorNote:
    note_id: str
    text: str
    created_at: str
    kind: str = "draft"  # draft | note

    def to_payload(self) -> dict[str, Any]:
        return {
            "note_id": self.note_id,
            "text": self.text,
            "created_at": self.created_at,
            "kind": self.kind,
            # A note/draft is never an instruction or consent.
            "is_instruction": False,
            "is_consent": False,
            **_frozen(),
        }


@dataclass
class ExcitonControlRequest:
    request_id: str
    control: ExcitonControlKind
    operator: str = "local-operator"
    payload: dict[str, Any] = field(default_factory=dict)

    def to_payload(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "control": self.control.value,
            "operator": self.operator,
            "payload": self.payload,
            # A request is not an approval.
            "is_approval": False,
            **_frozen(),
        }


@dataclass
class ExcitonControlDecision:
    request_id: str
    control: ExcitonControlKind
    decision: ExcitonControlDecisionKind
    reason: str

    @property
    def allowed_read_only(self) -> bool:
        return self.decision == ExcitonControlDecisionKind.ALLOW_READ_ONLY

    def to_payload(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "control": self.control.value,
            "decision": self.decision.value,
            "reason": self.reason,
            # No decision is ever permission or authority.
            **_frozen(),
        }


@dataclass
class ExcitonReceipt:
    receipt_id: str
    kind: str  # snapshot | control
    created_at: str
    ref_hash: str | None = None
    detail: dict[str, Any] = field(default_factory=dict)

    def to_payload(self) -> dict[str, Any]:
        payload = {
            "schema": "exciton-receipt",
            "version": EXCITON_SCHEMA_VERSION,
            "receipt_id": self.receipt_id,
            "kind": self.kind,
            "created_at": self.created_at,
            "ref_hash": self.ref_hash,
            "detail": self.detail,
            **_frozen(),
        }
        payload["content_hash"] = exciton_hash(payload)
        return payload


@dataclass
class ExcitonStatusSnapshot:
    snapshot_id: str
    generated_at: str
    chrono_ref: str | None
    overall_verdict: str
    panels: list[ExcitonPanelStatus] = field(default_factory=list)
    refresh_policy: ExcitonRefreshPolicy = field(default_factory=ExcitonRefreshPolicy)
    operator_notes: list[ExcitonOperatorNote] = field(default_factory=list)
    dangerous_actions_disabled: bool = True
    stop_available: bool = True
    panic_available: bool = True
    warnings: list[str] = field(default_factory=list)

    def panel_ids(self) -> list[str]:
        return [p.panel_id for p in self.panels]

    def to_payload(self) -> dict[str, Any]:
        payload = {
            "schema": "exciton-status-snapshot",
            "version": EXCITON_SCHEMA_VERSION,
            "snapshot_id": self.snapshot_id,
            "generated_at": self.generated_at,
            "chrono_ref": self.chrono_ref,
            "overall_verdict": self.overall_verdict,
            "dangerous_actions_disabled": self.dangerous_actions_disabled,
            "stop_available": self.stop_available,
            "panic_available": self.panic_available,
            "refresh_policy": self.refresh_policy.to_payload(),
            "panels": [p.to_payload() for p in self.panels],
            "operator_notes": [n.to_payload() for n in self.operator_notes],
            "warnings": self.warnings,
            **_frozen(),
        }
        payload["snapshot_hash"] = exciton_hash(payload)
        return payload


__all__ = [
    "EXCITON_SCHEMA_VERSION",
    "FIXTURE_RUN_ID",
    "FIXTURE_UTC",
    "HASH_EXCLUDE_KEYS",
    "ExcitonControlDecision",
    "ExcitonControlDecisionKind",
    "ExcitonControlKind",
    "ExcitonControlRequest",
    "ExcitonDegradedState",
    "ExcitonOperatorNote",
    "ExcitonPanelState",
    "ExcitonPanelStatus",
    "ExcitonProofLink",
    "ExcitonReceipt",
    "ExcitonRefreshPolicy",
    "ExcitonStatusSnapshot",
    "exciton_hash",
    "new_id",
]
