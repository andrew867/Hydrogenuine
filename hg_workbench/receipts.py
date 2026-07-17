"""Workbench chained receipts — canonical-hash + previous_receipt_hash + seq.

Modeled on hg_operator_auth.OperatorDecisionReceipt so the proofkit hash-chain
checker validates a Workbench receipt chain unchanged. Every receipt carries its
run_id (INV-RUN-ISO), a monotonic seq, and never any raw token.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Optional

from hg_core.governance.canonical_hash import canonical_hash

RECEIPT_SCHEMA_VERSION = "1.0"
_JWT_RE = re.compile(r"eyJ[A-Za-z0-9_-]{10,}")


class WorkbenchReceiptError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _hash_body(payload: dict[str, Any]) -> str:
    body = {k: v for k, v in payload.items() if k != "receipt_hash"}
    return canonical_hash(body)


@dataclass(frozen=True)
class _BaseReceipt:
    receipt_id: str
    run_id: str
    seq: int
    at: str
    previous_receipt_hash: Optional[str] = None
    receipt_hash: str = field(init=False)

    def _schema(self) -> str:
        raise NotImplementedError

    def _body(self) -> dict[str, Any]:
        raise NotImplementedError

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload = {
            "schema": self._schema(),
            "schema_version": RECEIPT_SCHEMA_VERSION,
            "receipt_id": self.receipt_id,
            "run_id": self.run_id,
            "seq": self.seq,
            "at": self.at,
            "previous_receipt_hash": self.previous_receipt_hash,
            **self._body(),
        }
        if include_hash:
            payload["receipt_hash"] = self.receipt_hash
        return payload

    def __post_init__(self) -> None:
        object.__setattr__(self, "receipt_hash",
                           _hash_body(self.to_payload(include_hash=False)))


@dataclass(frozen=True)
class WorkbenchRunReceipt(_BaseReceipt):
    operator_subject: str = ""
    session_id_hash: str = ""
    request_hash: str = ""           # hash of request text, not the text
    workflow_id: str = ""
    risk_level: str = ""
    external_effects_enabled: bool = False

    def _schema(self) -> str:
        return "hg-workbench-run-receipt"

    def _body(self) -> dict[str, Any]:
        return {"kind": "run_created", "operator_subject": self.operator_subject,
                "session_id_hash": self.session_id_hash,
                "request_hash": self.request_hash, "workflow_id": self.workflow_id,
                "risk_level": self.risk_level,
                "external_effects_enabled": self.external_effects_enabled}


@dataclass(frozen=True)
class ArtifactReceipt(_BaseReceipt):
    artifact_id: str = ""
    filename: str = ""
    content_hash: str = ""
    source: str = ""
    # Additive fields for byte uploads (source="upload_bytes"): a path *reference*
    # inside the run dir and the server-computed size — never the raw bytes.
    stored_path_ref: Optional[str] = None
    size_bytes: Optional[int] = None
    label: str = ""

    def _schema(self) -> str:
        return "hg-workbench-artifact-receipt"

    def _body(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "kind": "artifact_registered", "artifact_id": self.artifact_id,
            "filename": self.filename, "content_hash": self.content_hash,
            "source": self.source}
        # Emit the upload-only fields only when present so existing metadata-only
        # receipts hash identically (backward-compatible chain).
        if self.stored_path_ref is not None:
            body["stored_path_ref"] = self.stored_path_ref
        if self.size_bytes is not None:
            body["size_bytes"] = self.size_bytes
        if self.label:
            body["label"] = self.label
        return body


@dataclass(frozen=True)
class ProgressEventReceipt(_BaseReceipt):
    event_id: str = ""
    event_type: str = ""
    subagent_lane_id: Optional[str] = None
    authority: bool = False          # always False

    def _schema(self) -> str:
        return "hg-workbench-progress-receipt"

    def _body(self) -> dict[str, Any]:
        return {"kind": "progress_event", "event_id": self.event_id,
                "event_type": self.event_type,
                "subagent_lane_id": self.subagent_lane_id,
                "authority": self.authority}


@dataclass(frozen=True)
class SteeringReceipt(_BaseReceipt):
    message_id: str = ""
    text_hash: str = ""
    authority: str = "advice_not_authority"

    def _schema(self) -> str:
        return "hg-workbench-steering-receipt"

    def _body(self) -> dict[str, Any]:
        return {"kind": "steering_message", "message_id": self.message_id,
                "text_hash": self.text_hash, "authority": self.authority}


@dataclass(frozen=True)
class SettingChangeReceipt(_BaseReceipt):
    change_id: str = ""
    setting: str = ""
    action_class: str = ""
    new_value_hash: str = ""
    applied: bool = False
    hold_reason: str = ""

    def _schema(self) -> str:
        return "hg-workbench-setting-receipt"

    def _body(self) -> dict[str, Any]:
        return {"kind": "setting_change", "change_id": self.change_id,
                "setting": self.setting, "action_class": self.action_class,
                "new_value_hash": self.new_value_hash, "applied": self.applied,
                "hold_reason": self.hold_reason}


def validate_no_raw_token(receipt: _BaseReceipt) -> None:
    if _JWT_RE.search(str(receipt.to_payload())):
        raise WorkbenchReceiptError("raw_token_in_receipt")


def verify_run_chain(payloads: list[dict[str, Any]]) -> dict[str, Any]:
    """Recompute each hash + check previous_receipt_hash linkage + monotonic seq.

    Enforces INV-RUN-ISO: every receipt in the chain shares one run_id.
    """
    failures: list[str] = []
    previous: Optional[str] = None
    run_ids = set()
    last_seq = -1
    for index, payload in enumerate(payloads):
        run_ids.add(payload.get("run_id"))
        body = {k: v for k, v in payload.items() if k != "receipt_hash"}
        if canonical_hash(body) != payload.get("receipt_hash"):
            failures.append(f"hash_mismatch_at_{index}")
        if payload.get("previous_receipt_hash") != previous:
            failures.append(f"link_broken_at_{index}")
        seq = payload.get("seq", -1)
        if seq <= last_seq:
            failures.append(f"seq_not_monotonic_at_{index}")
        last_seq = seq
        previous = payload.get("receipt_hash")
        if _JWT_RE.search(str(payload)):
            failures.append(f"raw_token_at_{index}")
    if len(run_ids) > 1:
        failures.append(f"cross_run_chain:{sorted(str(r) for r in run_ids)}")
    return {"ok": not failures, "count": len(payloads),
            "run_id": next(iter(run_ids), None), "failures": failures}


__all__ = [
    "ArtifactReceipt", "ProgressEventReceipt", "SettingChangeReceipt",
    "SteeringReceipt", "WorkbenchReceiptError", "WorkbenchRunReceipt",
    "validate_no_raw_token", "verify_run_chain",
]
