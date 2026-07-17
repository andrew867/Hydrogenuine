"""OpenSSL-compatible Ed25519 signing key generation."""

from __future__ import annotations

import hashlib
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from hg_runtime.anchor_signing.keyring import export_public_key_file, load_signing_key
from hg_runtime.github_anchor_repo_init.hygiene import restrict_private_permissions, verify_key_hygiene
from hg_runtime.github_anchor_repo_init.paths import DEFAULT_SIGNING_DIR, WORKSPACE


@dataclass
class SigningKeyInitResult:
    private_key_path: Path
    public_key_path: Path
    signer_key_id: str
    public_key_sha256: str
    public_export_path: Path | None
    created: bool
    method: str
    verdict: str

    def to_payload(self) -> dict:
        return {
            "schema": "anchor-signing-key-init",
            "verdict": self.verdict,
            "signer_key_id": self.signer_key_id,
            "public_key_sha256": self.public_key_sha256,
            "private_key_path": "[REDACTED]",
            "public_key_path": str(self.public_key_path),
            "public_export_path": str(self.public_export_path) if self.public_export_path else None,
            "created": self.created,
            "method": self.method,
            "private_key_printed": False,
            "advisory_only": True,
            "permission_granted": False,
            "authority_created": False,
        }


def _resolve_paths(out_dir: Path | None) -> tuple[Path, Path]:
    base = out_dir or DEFAULT_SIGNING_DIR
    priv_env = os.environ.get("HG_ANCHOR_SIGNING_PRIVATE_KEY_PATH", "").strip()
    pub_env = os.environ.get("HG_ANCHOR_SIGNING_PUBLIC_KEY_PATH", "").strip()
    if out_dir is not None:
        return base / "agent_zero_anchor_ed25519.pem", base / "agent_zero_anchor_ed25519.pub.pem"
    private_path = Path(priv_env) if priv_env else base / "agent_zero_anchor_ed25519.pem"
    public_path = Path(pub_env) if pub_env else base / "agent_zero_anchor_ed25519.pub.pem"
    if not private_path.is_absolute():
        private_path = WORKSPACE / private_path
    if not public_path.is_absolute():
        public_path = WORKSPACE / public_path
    return private_path, public_path


def _openssl_available() -> bool:
    proc = subprocess.run(["openssl", "version"], capture_output=True, text=True, check=False)
    return proc.returncode == 0


def _generate_openssl(private_path: Path, public_path: Path) -> None:
    private_path.parent.mkdir(parents=True, exist_ok=True)
    gen = subprocess.run(
        ["openssl", "genpkey", "-algorithm", "Ed25519", "-out", str(private_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    if gen.returncode != 0:
        raise RuntimeError(gen.stderr.strip() or "openssl genpkey failed")
    pub = subprocess.run(
        ["openssl", "pkey", "-in", str(private_path), "-pubout", "-out", str(public_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    if pub.returncode != 0:
        raise RuntimeError(pub.stderr.strip() or "openssl pkey -pubout failed")
    restrict_private_permissions(private_path)
    restrict_private_permissions(public_path)


def _generate_cryptography(private_path: Path, public_path: Path) -> None:
    private_path.parent.mkdir(parents=True, exist_ok=True)
    private_key = Ed25519PrivateKey.generate()
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    private_path.write_bytes(private_pem)
    public_path.write_bytes(public_pem)
    restrict_private_permissions(private_path)
    restrict_private_permissions(public_path)


def generate_signing_key(
    *,
    out_dir: Path | None = None,
    force: bool = False,
    export_public: bool = True,
) -> SigningKeyInitResult:
    private_path, public_path = _resolve_paths(out_dir)
    created = False
    method = "existing"

    if private_path.exists() and public_path.exists() and not force:
        key = load_signing_key(out_dir=out_dir)
    else:
        if _openssl_available():
            try:
                _generate_openssl(private_path, public_path)
                method = "openssl"
            except RuntimeError:
                _generate_cryptography(private_path, public_path)
                method = "cryptography"
        else:
            _generate_cryptography(private_path, public_path)
            method = "cryptography"
        created = True
        os.environ.setdefault("HG_ANCHOR_SIGNING_PRIVATE_KEY_PATH", str(private_path))
        os.environ.setdefault("HG_ANCHOR_SIGNING_PUBLIC_KEY_PATH", str(public_path))
        key = load_signing_key(out_dir=out_dir)

    hygiene = verify_key_hygiene(private_path, workspace=WORKSPACE)
    if hygiene["private_key_tracked"]:
        raise ValueError("RED_PRIVATE_KEY_TRACKED")

    export_path = export_public_key_file(out_dir) if export_public else None
    pub_bytes = serialization.load_pem_public_key(public_path.read_bytes()).public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    signer_id = hashlib.sha256(pub_bytes).hexdigest()
    return SigningKeyInitResult(
        private_key_path=private_path,
        public_key_path=public_path,
        signer_key_id=signer_id,
        public_key_sha256=signer_id,
        public_export_path=export_path,
        created=created,
        method=method,
        verdict="GREEN_ANCHOR_SIGNING_KEY_READY",
    )


__all__ = ["SigningKeyInitResult", "generate_signing_key"]
