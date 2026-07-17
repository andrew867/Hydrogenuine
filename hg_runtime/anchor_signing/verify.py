"""Verify anchor/journal signatures."""

from __future__ import annotations

from typing import Any

import hashlib

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.exceptions import InvalidSignature

from hg_runtime.anchor_signing.schema import AnchorSignature, AnchorSignatureVerification
from hg_runtime.external_start_anchor.canonical_json import canonical_json_bytes, sha256_hex


class BadSignatureAccepted(Exception):
    code = "RED_BAD_SIGNATURE_ACCEPTED"


def load_public_key_from_pem(pem: str) -> Ed25519PublicKey:
    key = serialization.load_pem_public_key(pem.encode("utf-8"))
    assert isinstance(key, Ed25519PublicKey)
    return key


def verify_signature(
    payload: dict[str, Any],
    signature: AnchorSignature | dict[str, Any],
    *,
    public_key_pem: str,
    strict: bool = True,
) -> AnchorSignatureVerification:
    failures: list[str] = []
    sig = signature if isinstance(signature, AnchorSignature) else AnchorSignature(**{k: signature[k] for k in (
        "signer_key_id", "signature_algorithm", "signature", "signed_payload_sha256",
        "previous_signature_sha256", "public_key_sha256", "created_utc",
    ) if k in signature})
    clean = {k: v for k, v in payload.items() if k not in ("anchor_signature", "journal_signature")}
    computed_hash = sha256_hex(clean)
    if sig.signed_payload_sha256 != computed_hash:
        failures.append("payload hash mismatch")
    expected_key_id = hashlib.sha256(
        load_public_key_from_pem(public_key_pem).public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
    ).hexdigest()
    if sig.signer_key_id != expected_key_id:
        failures.append("signer_key_id mismatch")
    if clean.get("authority") is True or clean.get("permission") is True:
        failures.append("RED_AUTHORITY_CONVERSION")
    if clean.get("permission_granted") is True or clean.get("authority_created") is True:
        failures.append("RED_AUTHORITY_CONVERSION")
    try:
        pub = load_public_key_from_pem(public_key_pem)
        pub.verify(bytes.fromhex(sig.signature), canonical_json_bytes(clean))
    except (InvalidSignature, ValueError):
        failures.append("signature invalid")
    ok = not failures
    if not ok and strict:
        raise BadSignatureAccepted("; ".join(failures))
    return AnchorSignatureVerification(ok=ok, signer_key_id=sig.signer_key_id, failures=failures)


__all__ = ["BadSignatureAccepted", "load_public_key_from_pem", "verify_signature"]
