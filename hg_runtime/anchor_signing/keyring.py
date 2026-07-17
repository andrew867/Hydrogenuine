"""Anchor signing key management."""

from __future__ import annotations

import hashlib
import json
import os
import stat
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from hg_runtime.anchor_signing.schema import FROZEN_FALSE
from hg_runtime.external_start_anchor.canonical_json import sha256_hex

DEFAULT_SIGNING_DIR = Path(".hg-local") / "anchor_signing"
PRIVATE_KEY_NAME = "agent_zero_anchor_ed25519.pem"
PUBLIC_KEY_NAME = "agent_zero_anchor_ed25519.pub.pem"
LEGACY_PRIVATE_KEY_NAME = "agent_zero_anchor_ed25519.key"
LEGACY_PUBLIC_KEY_NAME = "agent_zero_anchor_ed25519.pub"


@dataclass
class AnchorSigningKey:
    private_key_path: Path
    public_key_path: Path
    signer_key_id: str
    public_key_sha256: str
    public_key_pem: str

    def to_public_export(self) -> dict:
        return {
            "schema": "agent-zero-anchor-signing-public-key",
            "signer_key_id": self.signer_key_id,
            "public_key_sha256": self.public_key_sha256,
            "algorithm": "Ed25519",
            "public_key_pem": self.public_key_pem,
            "created_utc": datetime.now(timezone.utc).isoformat(),
            **FROZEN_FALSE,
        }


def _resolve_paths(out_dir: Path | None = None) -> tuple[Path, Path]:
    priv_env = os.environ.get("HG_ANCHOR_SIGNING_PRIVATE_KEY_PATH", "")
    pub_env = os.environ.get("HG_ANCHOR_SIGNING_PUBLIC_KEY_PATH", "")
    base = out_dir or DEFAULT_SIGNING_DIR
    if priv_env:
        private_path = Path(priv_env)
    elif (base / PRIVATE_KEY_NAME).exists():
        private_path = base / PRIVATE_KEY_NAME
    elif (base / LEGACY_PRIVATE_KEY_NAME).exists():
        private_path = base / LEGACY_PRIVATE_KEY_NAME
    else:
        private_path = base / PRIVATE_KEY_NAME
    if pub_env:
        public_path = Path(pub_env)
    elif (base / PUBLIC_KEY_NAME).exists():
        public_path = base / PUBLIC_KEY_NAME
    elif (base / LEGACY_PUBLIC_KEY_NAME).exists():
        public_path = base / LEGACY_PUBLIC_KEY_NAME
    else:
        public_path = base / PUBLIC_KEY_NAME
    return private_path, public_path


def _restrict_permissions(path: Path) -> None:
    try:
        path.chmod(stat.S_IRUSR | stat.S_IWUSR)
    except OSError:
        pass


def key_exists(out_dir: Path | None = None) -> bool:
    private_path, public_path = _resolve_paths(out_dir)
    return private_path.exists() and public_path.exists()


def load_signing_key(out_dir: Path | None = None) -> AnchorSigningKey:
    private_path, public_path = _resolve_paths(out_dir)
    if not private_path.exists() or not public_path.exists():
        raise FileNotFoundError("YELLOW_SIGNING_KEY_NOT_INITIALIZED")
    private_key = serialization.load_pem_private_key(private_path.read_bytes(), password=None)
    public_pem = public_path.read_text(encoding="utf-8")
    public_key = serialization.load_pem_public_key(public_pem.encode("utf-8"))
    pub_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    signer_key_id = hashlib.sha256(pub_bytes).hexdigest()
    return AnchorSigningKey(
        private_key_path=private_path,
        public_key_path=public_path,
        signer_key_id=signer_key_id,
        public_key_sha256=signer_key_id,
        public_key_pem=public_pem,
    )


def init_signing_key(*, out_dir: Path | None = None, rotate: bool = False) -> AnchorSigningKey:
    private_path, public_path = _resolve_paths(out_dir)
    if key_exists(out_dir) and not rotate:
        return load_signing_key(out_dir)
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
    _restrict_permissions(private_path)
    _restrict_permissions(public_path)
    return load_signing_key(out_dir)


def export_public_key_file(out_dir: Path | None = None) -> Path:
    key = load_signing_key(out_dir)
    export_path = (out_dir or DEFAULT_SIGNING_DIR) / "current_public_key.json"
    export_path.write_text(json.dumps(key.to_public_export(), indent=2) + "\n", encoding="utf-8")
    history = (out_dir or DEFAULT_SIGNING_DIR) / "history"
    history.mkdir(parents=True, exist_ok=True)
    (history / f"{key.signer_key_id}.json").write_text(json.dumps(key.to_public_export(), indent=2) + "\n", encoding="utf-8")
    return export_path


__all__ = [
    "AnchorSigningKey",
    "DEFAULT_SIGNING_DIR",
    "export_public_key_file",
    "init_signing_key",
    "key_exists",
    "load_signing_key",
]
