"""Sign canonical anchor/journal payloads."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from hg_runtime.anchor_signing.keyring import AnchorSigningKey, load_signing_key
from hg_runtime.anchor_signing.schema import AnchorSignature, SignedAnchorEnvelope, SignedJournalEvent
from hg_runtime.external_start_anchor.canonical_json import canonical_json_bytes, sha256_hex


def _sign_bytes(private_key: Ed25519PrivateKey, payload: dict[str, Any]) -> tuple[str, str]:
    digest = sha256_hex(payload)
    sig = private_key.sign(canonical_json_bytes(payload))
    return digest, sig.hex()


def sign_payload(
    payload: dict[str, Any],
    *,
    signing_key: AnchorSigningKey | None = None,
    previous_signature_sha256: str | None = None,
) -> AnchorSignature:
    key = signing_key or load_signing_key()
    private_key = serialization.load_pem_private_key(key.private_key_path.read_bytes(), password=None)
    assert isinstance(private_key, Ed25519PrivateKey)
    signed_payload_sha256, signature_hex = _sign_bytes(private_key, payload)
    return AnchorSignature(
        signer_key_id=key.signer_key_id,
        signature=signature_hex,
        signed_payload_sha256=signed_payload_sha256,
        previous_signature_sha256=previous_signature_sha256,
        public_key_sha256=key.public_key_sha256,
        created_utc=datetime.now(timezone.utc).isoformat(),
    )


def sign_public_anchor(payload: dict[str, Any], **kwargs: Any) -> SignedAnchorEnvelope:
    clean = {k: v for k, v in payload.items() if k not in ("anchor_signature", "journal_signature")}
    sig = sign_payload(clean, **kwargs)
    return SignedAnchorEnvelope(payload=clean, signature=sig)


def sign_journal_event(payload: dict[str, Any], **kwargs: Any) -> SignedJournalEvent:
    clean = {k: v for k, v in payload.items() if k not in ("anchor_signature", "journal_signature")}
    sig = sign_payload(clean, **kwargs)
    return SignedJournalEvent(payload=clean, signature=sig)


__all__ = ["sign_journal_event", "sign_payload", "sign_public_anchor"]
