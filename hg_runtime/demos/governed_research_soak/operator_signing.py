"""Ephemeral Ed25519 signing for local demo operator decisions.

Generates a one-time keypair per run. The private key never leaves the
process. The public key is written to operator_identity.json so the gate
can verify decision signatures.

This is a LOCAL DEMO signing mechanism. It does NOT constitute
production human identity verification.
"""

from __future__ import annotations

import base64
import hashlib
import json
from datetime import datetime, timezone

from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    PublicFormat,
    NoEncryption,
    PrivateFormat,
)


class OperatorSigner:
    def __init__(self):
        self._private_key = Ed25519PrivateKey.generate()
        self._public_key = self._private_key.public_key()
        pub_bytes = self._public_key.public_bytes(Encoding.Raw, PublicFormat.Raw)
        self.public_key_b64 = base64.b64encode(pub_bytes).decode("ascii")
        self.fingerprint = "sha256:" + hashlib.sha256(pub_bytes).hexdigest()[:16]
        self.operator_id = f"operator-local-{self.fingerprint[7:15]}"

    def sign(self, payload: dict) -> str:
        canonical = json.dumps(
            payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        )
        sig_bytes = self._private_key.sign(canonical.encode("utf-8"))
        return base64.b64encode(sig_bytes).decode("ascii")

    def identity_record(self) -> dict:
        return {
            "operator_id": self.operator_id,
            "operator_mode": "claude_code_local_signed_operator",
            "operator_identity_type": "local_demo_signed_operator",
            "operator_auth_scope": "demo_local_only",
            "production_operator_auth": False,
            "public_key_algorithm": "Ed25519",
            "public_key_b64": self.public_key_b64,
            "key_fingerprint": self.fingerprint,
            "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }

    def sign_decision(
        self,
        *,
        action: str,
        target_candidate_id: str,
        reason: str,
        receipt_ids_reviewed: list[str],
    ) -> dict:
        payload = {
            "operator_id": self.operator_id,
            "operator_mode": "claude_code_local_signed_operator",
            "operator_identity_type": "local_demo_signed_operator",
            "decision_source": "browser_ui_click",
            "decision_action": action,
            "target_candidate_id": target_candidate_id,
            "decision_reason": reason,
            "receipt_ids_reviewed": receipt_ids_reviewed,
            "decision_timestamp": datetime.now(timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            ),
            "production_operator_auth": False,
        }
        payload_hash = "sha256:" + hashlib.sha256(
            json.dumps(
                payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
            ).encode("utf-8")
        ).hexdigest()
        payload["payload_hash"] = payload_hash
        payload["signature"] = self.sign(payload)
        return payload


def verify_signature(public_key_b64: str, payload: dict) -> bool:
    """Verify an Ed25519 signature on a decision payload."""
    sig_b64 = payload.get("signature", "")
    if not sig_b64:
        return False
    check_payload = {k: v for k, v in payload.items() if k != "signature"}
    canonical = json.dumps(
        check_payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    )
    pub_bytes = base64.b64decode(public_key_b64)
    pub_key = Ed25519PublicKey.from_public_bytes(pub_bytes)
    try:
        pub_key.verify(base64.b64decode(sig_b64), canonical.encode("utf-8"))
        return True
    except Exception:
        return False
