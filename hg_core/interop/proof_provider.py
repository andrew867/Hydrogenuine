"""
Interop Pack 1: ProofProvider interface — pluggable signatures, attestations, proofs.
"""
from __future__ import annotations

import hashlib
from typing import Any, Dict, Optional, Protocol


class ProofProvider(Protocol):
    def sign(self, payload: bytes, context: Dict[str, Any]) -> Dict[str, Any]: ...
    def verify_signature(self, payload: bytes, sig: Dict[str, Any], context: Dict[str, Any]) -> bool: ...
    def attest(self, execution: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]: ...
    def verify_attestation(self, att: Dict[str, Any], context: Dict[str, Any]) -> bool: ...


_default_provider: Optional[Any] = None


def get_proof_provider() -> Optional[ProofProvider]:
    return _default_provider


def set_proof_provider(provider: ProofProvider) -> None:
    global _default_provider
    _default_provider = provider


class DefaultProofProvider:
    """Signature-only implementation (no TEE/ZK)."""
    def sign(self, payload: bytes, context: Dict[str, Any]) -> Dict[str, Any]:
        return {"alg": "sha256_hex", "value": hashlib.sha256(payload).hexdigest()}
    def verify_signature(self, payload: bytes, sig: Dict[str, Any], context: Dict[str, Any]) -> bool:
        if sig.get("alg") != "sha256_hex":
            return False
        return hashlib.sha256(payload).hexdigest() == sig.get("value", "")
    def attest(self, execution: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        import json
        return {"profile": "default", "claims": execution, "signature": self.sign(json.dumps(execution, sort_keys=True).encode(), context)}
    def verify_attestation(self, att: Dict[str, Any], context: Dict[str, Any]) -> bool:
        if not att.get("claims") or not att.get("signature"):
            return False
        import json
        return self.verify_signature(json.dumps(att["claims"], sort_keys=True).encode(), att["signature"], context)
