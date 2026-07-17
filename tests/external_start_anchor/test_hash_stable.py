"""Canonical hash stability tests."""

from __future__ import annotations

from hg_runtime.external_start_anchor.boot_bundle import build_boot_bundle
from hg_runtime.external_start_anchor.hash_bundle import hash_boot_bundle, hash_public_anchor
from hg_runtime.external_start_anchor.public_anchor import PRIVATE_BOOT_FIELDS, build_public_anchor
from hg_runtime.external_start_anchor.schema import GitHubAnchorConfig
from hg_runtime.trust_boundary.secrets import SecretGuard


def test_boot_bundle_hash_stable():
    cfg = GitHubAnchorConfig()
    boot = build_boot_bundle(cfg, sequence=0)
    boot.created_utc = "2026-06-15T00:00:00+00:00"
    h1 = hash_boot_bundle(boot)
    h2 = hash_boot_bundle(boot)
    assert h1 == h2
    assert len(h1) == 64


def test_public_anchor_excludes_private_fields():
    cfg = GitHubAnchorConfig()
    boot = build_boot_bundle(cfg, sequence=1)
    boot.created_utc = "2026-06-15T00:00:00+00:00"
    public = build_public_anchor(boot)
    data = public.to_dict()
    for field in PRIVATE_BOOT_FIELDS:
        assert field not in data
    assert public.authority is False
    assert public.permission is False
    assert public.secrets is False


def test_public_anchor_no_secrets():
    cfg = GitHubAnchorConfig()
    boot = build_boot_bundle(cfg, sequence=2, operator_note="continuity witness only")
    public = build_public_anchor(boot)
    assert not SecretGuard.contains_secret(str(public.to_dict()))


def test_timestamp_changes_hash():
    cfg = GitHubAnchorConfig()
    b1 = build_boot_bundle(cfg, sequence=3)
    b1.created_utc = "2026-06-15T00:00:00+00:00"
    b2 = build_boot_bundle(cfg, sequence=3)
    b2.created_utc = "2026-06-15T01:00:00+00:00"
    assert hash_boot_bundle(b1) != hash_boot_bundle(b2)
