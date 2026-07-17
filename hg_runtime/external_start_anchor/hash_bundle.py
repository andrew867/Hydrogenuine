"""Hash helpers for anchor bundles."""

from __future__ import annotations

from hg_runtime.external_start_anchor.canonical_json import sha256_hex
from hg_runtime.external_start_anchor.schema import AnchorHash, BootContinuityBundle, PublicAnchorBundle


def hash_boot_bundle(bundle: BootContinuityBundle) -> str:
    return sha256_hex(bundle.to_dict())


def hash_public_anchor(bundle: PublicAnchorBundle) -> str:
    payload = bundle.to_dict()
    # public_anchor_sha256 is self-referential; exclude for stable pre-commit hash
    payload.pop("public_anchor_sha256", None)
    payload.pop("github_anchor_commit", None)
    return sha256_hex(payload)


def anchor_hashes(boot: BootContinuityBundle, public: PublicAnchorBundle) -> AnchorHash:
    boot_hash = hash_boot_bundle(boot)
    public.boot_bundle_sha256 = boot_hash
    pub_hash = hash_public_anchor(public)
    public.public_anchor_sha256 = pub_hash
    return AnchorHash(boot_bundle_sha256=boot_hash, public_anchor_sha256=pub_hash)


__all__ = ["anchor_hashes", "hash_boot_bundle", "hash_public_anchor"]
