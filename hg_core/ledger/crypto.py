"""
Ed25519 sign/verify for ledger events.

- With pynacl installed: real Ed25519 sign/verify; tampering or wrong key fails.
- Without pynacl: dev/CI stub — sign() returns a fixed stub, verify() accepts only that stub.
  Envelope format and hash chain are still validated; no security guarantee. By design for
  environments that omit pynacl (e.g. minimal CI). Production should install pynacl and
  supply real keys.
"""

from __future__ import annotations

import os
from typing import Optional, Tuple

try:
    import nacl.encoding
    import nacl.signing
    _NACL = True
except ImportError:
    _NACL = False


def strict_crypto_required() -> bool:
    """True when stub signatures must not be used (production-like runtime)."""
    env = (os.environ.get("HG_ENV", "Demo") or "Demo").strip().lower()
    dev = os.environ.get("HG_GATEWAY_DEV", "").strip().lower() in ("1", "true", "yes")
    force = os.environ.get("HG_LEDGER_REQUIRE_PYNACL", "").strip().lower() in ("1", "true", "yes")
    if force:
        return True
    return env not in {"demo", "dev", "development", "test", "testing"} and not dev


def _reject_stub_crypto(operation: str) -> None:
    if not _NACL and strict_crypto_required():
        raise RuntimeError(
            f"Ledger {operation} requires pynacl in non-demo mode. "
            "pip install pynacl and configure real signing keys."
        )


def generate_keypair() -> Tuple[str, str]:
    """
    Generate (secret_key_hex, public_key_hex). Requires pynacl.
    Raises RuntimeError if pynacl not installed.
    """
    if not _NACL:
        raise RuntimeError("pynacl required for generate_keypair(); pip install pynacl")
    sk = nacl.signing.SigningKey.generate()
    pk = sk.verify_key
    return sk.encode(encoder=nacl.encoding.HexEncoder).decode("ascii"), pk.encode(encoder=nacl.encoding.HexEncoder).decode("ascii")


def sign(message: bytes, secret_key_hex: str) -> str:
    """Sign message with Ed25519; return signature hex. Stub returns zeros if pynacl missing (demo only)."""
    _reject_stub_crypto("sign")
    if _NACL:
        sk = nacl.signing.SigningKey(secret_key_hex.encode("ascii"), encoder=nacl.encoding.HexEncoder)
        sig = sk.sign(message)
        return sig.signature.hex()
    # Stub: deterministic "signature" for testing (same message -> same stub sig)
    return ("00" * 64)[:128]


def verify(message: bytes, signature_hex: str, public_key_hex: str) -> bool:
    """Verify Ed25519 signature. If pynacl missing, accept stub signatures in demo only."""
    _reject_stub_crypto("verify")
    if not _NACL:
        return signature_hex == ("00" * 64)[:128]
    try:
        pk = nacl.signing.VerifyKey(public_key_hex.encode("ascii"), encoder=nacl.encoding.HexEncoder)
        sig_bytes = bytes.fromhex(signature_hex)
        pk.verify(message, sig_bytes)
        return True
    except Exception:
        return False
