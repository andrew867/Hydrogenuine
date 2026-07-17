"""Signed public anchor helpers."""

from __future__ import annotations

from typing import Any

from hg_runtime.anchor_signing.keyring import key_exists, load_signing_key
from hg_runtime.anchor_signing.sign import sign_public_anchor
from hg_runtime.anchor_signing.verify import verify_signature
from hg_runtime.external_start_anchor.public_anchor import build_public_anchor
from hg_runtime.external_start_anchor.schema import BootContinuityBundle, PublicAnchorBundle


def build_signed_public_anchor(
    boot: BootContinuityBundle,
    *,
    github_commit: str | None = None,
    previous_signature_sha256: str | None = None,
    sign: bool = True,
) -> dict[str, Any]:
    public = build_public_anchor(boot, github_commit=github_commit)
    payload = public.to_dict()
    payload["signer_key_id"] = None
    payload["public_key_sha256"] = None
    if sign and key_exists():
        key = load_signing_key()
        payload["signer_key_id"] = key.signer_key_id
        payload["public_key_sha256"] = key.public_key_sha256
        envelope = sign_public_anchor(payload, previous_signature_sha256=previous_signature_sha256)
        return envelope.to_dict()
    return payload


def verify_signed_public_anchor(data: dict[str, Any], *, public_key_pem: str, strict: bool = True) -> bool:
    sig = data.get("anchor_signature")
    if not sig:
        return not strict
    verify_signature(data, sig, public_key_pem=public_key_pem, strict=strict)
    return True


def write_public_key_to_repo(repo, cfg, key) -> dict[str, str]:
    import json
    from pathlib import Path

    keys_dir = Path(repo) / "anchors" / "agent0" / "keys"
    keys_dir.mkdir(parents=True, exist_ok=True)
    current = keys_dir / "current_public_key.json"
    export = key.to_public_export()
    current.write_text(json.dumps(export, indent=2) + "\n", encoding="utf-8")
    history = keys_dir / "history" / f"{key.signer_key_id}.json"
    history.parent.mkdir(parents=True, exist_ok=True)
    history.write_text(json.dumps(export, indent=2) + "\n", encoding="utf-8")
    return {"current_public_key": str(current.relative_to(repo)), "history_key": str(history.relative_to(repo))}


__all__ = ["build_signed_public_anchor", "verify_signed_public_anchor", "write_public_key_to_repo"]
