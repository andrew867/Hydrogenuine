"""Organ reflection for self mirror."""

from __future__ import annotations

from hg_runtime.agent0_dev_boot.manifest import load_organ_manifest, manifest_digest
from hg_runtime.agent_zero_self_mirror.schema import IndexStatus, OrganIndex


def build_organ_index(*, last_heartbeat: dict[str, str] | None = None) -> OrganIndex:
    manifest = load_organ_manifest()
    organs = []
    hb = last_heartbeat or {}
    for organ in manifest.get("organs", []):
        oid = organ.get("organ_id", "")
        organs.append({
            "organ_id": oid,
            "name": organ.get("name", oid),
            "required": organ.get("required", False),
            "status": "boot_ready",
            "last_heartbeat": hb.get(oid),
            "last_receipt_ref": None,
            "boot_state": "pending_wake",
            "degraded": False,
            "advisory_only": True,
            "permission_granted": False,
            "authority_created": False,
        })
    return OrganIndex(status=IndexStatus.READY, organs=organs)


def organ_manifest_hash() -> str:
    return manifest_digest(load_organ_manifest())


__all__ = ["build_organ_index", "organ_manifest_hash"]
