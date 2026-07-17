"""Trust Boundary receipts and telemetry."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from hg_runtime.trust_boundary.hash import tb_hash
from hg_runtime.trust_boundary.schema import TaintLabel, new_id

TB_EVENT_TYPES = (
    "TB_INGRESS_LABELLED",
    "TB_INJECTION_SCANNED",
    "TB_INJECTION_ATTEMPT_RECORDED",
    "TB_SECRET_REDACTED",
    "TB_ADVISORY_PRODUCED",
    "TB_CONTENT_QUARANTINED",
    "TB_CONTENT_DROPPED",
    "TB_TOOL_REQUEST_REJECTED",
    "TB_RELABEL_REJECTED",
    "TB_SECRET_EXFILTRATION_BLOCKED",
    "TB_AUTHORITY_CONVERSION_REJECTED",
)


@dataclass
class IngressReceipt:
    label: TaintLabel
    origin: str
    receipt_id: str = ""

    def to_payload(self) -> dict[str, Any]:
        payload = {
            "schema": "tb-ingress-receipt",
            "receipt_id": self.receipt_id or new_id("tbingress"),
            "label": self.label.value,
            "origin": self.origin,
            "advisory_only": True,
            "permission_granted": False,
            "authority_created": False,
        }
        payload["content_hash"] = tb_hash(payload)
        return payload


@dataclass
class InjectionAttempt:
    origin: str
    signals: list[str]
    disposition: str

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema": "tb-injection-attempt",
            "origin": self.origin,
            "signals": self.signals,
            "disposition": self.disposition,
            "advisory_only": True,
            "permission_granted": False,
            "authority_created": False,
        }


@dataclass
class TrustBoundaryViolationRecord:
    code: str
    detail: str

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema": "tb-violation",
            "code": self.code,
            "detail": self.detail,
            "advisory_only": True,
            "permission_granted": False,
            "authority_created": False,
        }


__all__ = [
    "TB_EVENT_TYPES",
    "IngressReceipt",
    "InjectionAttempt",
    "TrustBoundaryViolationRecord",
]
