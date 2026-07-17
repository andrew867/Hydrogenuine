"""Anchor signing schema."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

SIGNATURE_ALGORITHM = "Ed25519"
FROZEN_FALSE = {
    "advisory_only": True,
    "permission_granted": False,
    "authority_created": False,
}


@dataclass
class AnchorSignature:
    signer_key_id: str
    signature_algorithm: str = SIGNATURE_ALGORITHM
    signature: str = ""
    signed_payload_sha256: str = ""
    previous_signature_sha256: str | None = None
    public_key_sha256: str = ""
    created_utc: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "signer_key_id": self.signer_key_id,
            "signature_algorithm": self.signature_algorithm,
            "signature": self.signature,
            "signed_payload_sha256": self.signed_payload_sha256,
            "previous_signature_sha256": self.previous_signature_sha256,
            "public_key_sha256": self.public_key_sha256,
            "created_utc": self.created_utc,
            **FROZEN_FALSE,
        }


@dataclass
class SignedAnchorEnvelope:
    payload: dict[str, Any]
    signature: AnchorSignature

    def to_dict(self) -> dict[str, Any]:
        return {**self.payload, "anchor_signature": self.signature.to_dict()}


@dataclass
class SignedJournalEvent:
    payload: dict[str, Any]
    signature: AnchorSignature

    def to_dict(self) -> dict[str, Any]:
        return {**self.payload, "journal_signature": self.signature.to_dict()}


@dataclass
class AnchorSignatureVerification:
    ok: bool
    signer_key_id: str | None = None
    failures: list[str] = field(default_factory=list)

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema": "anchor-signature-verification",
            "ok": self.ok,
            "signer_key_id": self.signer_key_id,
            "failures": self.failures,
            **FROZEN_FALSE,
        }


__all__ = [
    "AnchorSignature",
    "AnchorSignatureVerification",
    "SIGNATURE_ALGORITHM",
    "SignedAnchorEnvelope",
    "SignedJournalEvent",
]
