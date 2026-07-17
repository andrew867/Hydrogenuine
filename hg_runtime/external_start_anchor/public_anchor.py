"""Public anchor bundle — sanitized witness material only."""

from __future__ import annotations

from hg_runtime.external_start_anchor.hash_bundle import hash_boot_bundle, hash_public_anchor
from hg_runtime.external_start_anchor.schema import BootContinuityBundle, PublicAnchorBundle
from hg_runtime.trust_boundary.secrets import SecretGuard

PRIVATE_BOOT_FIELDS = {
    "will_profile_hash",
    "trust_boundary_policy_hash",
    "chrono_status_hash",
    "audio_io_status_hash",
    "model_provider_status_hash",
    "storage_status_hash",
    "baseline_gate_refs",
    "hydrogenuine_repo_head",
    "hydrogenuine_branch",
    "chrono_receipt_ref",
    "operator_public_note",
}


def build_public_anchor(
    boot: BootContinuityBundle,
    *,
    github_commit: str | None = None,
) -> PublicAnchorBundle:
    boot_hash = hash_boot_bundle(boot)
    head_short = boot.hydrogenuine_repo_head[:12] if boot.hydrogenuine_repo_head else None
    public = PublicAnchorBundle(
        agent_long_name=boot.agent_long_name,
        agent_short_name=boot.agent_short_name,
        agent_code_id=boot.agent_code_id,
        anchor_sequence=boot.anchor_sequence,
        created_utc=boot.created_utc,
        boot_bundle_sha256=boot_hash,
        epoch_lock_id=boot.epoch_lock_id,
        previous_anchor_sha256=boot.previous_anchor_sha256,
        hydrogenuine_repo_head_short=head_short,
        github_anchor_commit=github_commit,
        authority=False,
        permission=False,
        secrets=False,
    )
    public.public_anchor_sha256 = hash_public_anchor(public)
    assert_public_anchor_safe(public)
    return public


def assert_public_anchor_safe(public: PublicAnchorBundle) -> None:
    data = public.to_dict()
    for field in PRIVATE_BOOT_FIELDS:
        if field in data:
            raise ValueError(f"private field leaked to public anchor: {field}")
    if public.authority or public.permission or public.secrets:
        raise ValueError("public anchor authority/permission/secrets must be false")
    payload = str(data)
    if SecretGuard.contains_secret(payload):
        raise ValueError("public anchor contains secret-shaped content")


def public_anchor_txt(public: PublicAnchorBundle) -> str:
    return (
        f"Hydrogenuine Agent Zero GitHub Anchor sequence={public.anchor_sequence}\n"
        f"boot_bundle_sha256={public.boot_bundle_sha256}\n"
        f"epoch_lock_id={public.epoch_lock_id or 'none'}\n"
        f"public_anchor_sha256={public.public_anchor_sha256}\n"
        f"github_commit={public.github_anchor_commit or 'pending'}\n"
        f"note={public.note}\n"
    )


__all__ = ["PRIVATE_BOOT_FIELDS", "assert_public_anchor_safe", "build_public_anchor", "public_anchor_txt"]
