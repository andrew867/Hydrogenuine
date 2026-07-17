"""External Start Anchor receipts."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from hg_runtime.external_start_anchor.canonical_json import sha256_hex
from hg_runtime.external_start_anchor.schema import FROZEN_FALSE, AnchorConfidence


def new_id(prefix: str = "esa") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


@dataclass
class ExternalStartAnchorReceipt:
    receipt_id: str = ""
    run_id: str = ""
    anchor_sequence: int = 0
    boot_bundle_sha256: str = ""
    public_anchor_sha256: str = ""
    github_commit_sha: str | None = None
    backend: str = "github"
    dry_run: bool = True
    pushed: bool = False
    verified_after_push: bool = False
    created_utc: str = ""

    def to_payload(self) -> dict[str, Any]:
        payload = {
            "schema": "external-start-anchor-receipt",
            "receipt_id": self.receipt_id or new_id("esar"),
            "run_id": self.run_id,
            "anchor_sequence": self.anchor_sequence,
            "boot_bundle_sha256": self.boot_bundle_sha256,
            "public_anchor_sha256": self.public_anchor_sha256,
            "github_commit_sha": self.github_commit_sha,
            "backend": self.backend,
            "dry_run": self.dry_run,
            "pushed": self.pushed,
            "verified_after_push": self.verified_after_push,
            "created_utc": self.created_utc or datetime.now(timezone.utc).isoformat(),
            **FROZEN_FALSE,
        }
        payload["hash"] = sha256_hex({k: v for k, v in payload.items() if k != "hash"})
        return payload


@dataclass
class ExternalStartAnchorVerification:
    verification_id: str = ""
    status: str = "pending"
    confidence: AnchorConfidence = AnchorConfidence.UNKNOWN
    boot_bundle_sha256: str = ""
    public_anchor_sha256: str = ""
    github_commit_sha: str | None = None
    hash_match: bool = False
    authority_conversion: bool = False
    injection_detected: bool = False
    trust_boundary_receipt_ref: str | None = None
    verification_time_utc: str = ""
    detail: str = ""
    checks: list[dict[str, Any]] = field(default_factory=list)

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema": "external-start-anchor-verification",
            "verification_id": self.verification_id or new_id("esav"),
            "status": self.status,
            "confidence": self.confidence.value,
            "boot_bundle_sha256": self.boot_bundle_sha256,
            "public_anchor_sha256": self.public_anchor_sha256,
            "github_commit_sha": self.github_commit_sha,
            "hash_match": self.hash_match,
            "authority_conversion": self.authority_conversion,
            "injection_detected": self.injection_detected,
            "trust_boundary_receipt_ref": self.trust_boundary_receipt_ref,
            "verification_time_utc": self.verification_time_utc or datetime.now(timezone.utc).isoformat(),
            "detail": self.detail,
            "checks": self.checks,
            **FROZEN_FALSE,
        }


__all__ = ["ExternalStartAnchorReceipt", "ExternalStartAnchorVerification", "new_id"]
