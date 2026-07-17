"""Anchor signing tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from hg_runtime.anchor_signing.keyring import init_signing_key, key_exists, load_signing_key
from hg_runtime.anchor_signing.sign import sign_public_anchor
from hg_runtime.anchor_signing.verify import BadSignatureAccepted, verify_signature
from hg_runtime.external_start_anchor.signed_anchor import build_signed_public_anchor
from hg_runtime.external_start_anchor.boot_bundle import build_boot_bundle
from hg_runtime.external_start_anchor.schema import GitHubAnchorConfig


def test_signing_key_init(tmp_path: Path, monkeypatch):
    out = tmp_path / "signing"
    monkeypatch.setenv("HG_ANCHOR_SIGNING_PRIVATE_KEY_PATH", str(out / "priv.key"))
    monkeypatch.setenv("HG_ANCHOR_SIGNING_PUBLIC_KEY_PATH", str(out / "pub.key"))
    key = init_signing_key(out_dir=out)
    assert key.signer_key_id
    assert (out / "priv.key").exists()
    assert (out / "pub.key").exists()


def test_public_anchor_signs_and_verifies(tmp_path: Path, monkeypatch):
    out = tmp_path / "signing"
    monkeypatch.setenv("HG_ANCHOR_SIGNING_PRIVATE_KEY_PATH", str(out / "priv.key"))
    monkeypatch.setenv("HG_ANCHOR_SIGNING_PUBLIC_KEY_PATH", str(out / "pub.key"))
    init_signing_key(out_dir=out)
    cfg = GitHubAnchorConfig()
    boot = build_boot_bundle(cfg, sequence=0)
    boot.created_utc = "2026-06-15T00:00:00+00:00"
    signed = build_signed_public_anchor(boot, sign=True)
    assert "anchor_signature" in signed
    key = load_signing_key(out)
    verify_signature(signed, signed["anchor_signature"], public_key_pem=key.public_key_pem, strict=True)


def test_modified_anchor_fails(tmp_path: Path, monkeypatch):
    out = tmp_path / "signing"
    monkeypatch.setenv("HG_ANCHOR_SIGNING_PRIVATE_KEY_PATH", str(out / "priv.key"))
    monkeypatch.setenv("HG_ANCHOR_SIGNING_PUBLIC_KEY_PATH", str(out / "pub.key"))
    init_signing_key(out_dir=out)
    cfg = GitHubAnchorConfig()
    boot = build_boot_bundle(cfg, sequence=0)
    boot.created_utc = "2026-06-15T00:00:00+00:00"
    signed = build_signed_public_anchor(boot, sign=True)
    signed["boot_bundle_sha256"] = "deadbeef"
    key = load_signing_key(out)
    with pytest.raises(BadSignatureAccepted):
        verify_signature(signed, signed["anchor_signature"], public_key_pem=key.public_key_pem, strict=True)
