"""Organ manifest loader for Agent #0 dev boot."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from hg_core.policy_safety.hashing import compute_record_hash
from hg_runtime.agent0_dev_boot.types import advisory_payload

MANIFEST_PATH = Path(__file__).resolve().parents[2] / "configs" / "organs" / "agent0_dev_organ_manifest.json"


def load_organ_manifest(path: Path | None = None) -> dict[str, Any]:
    p = path or MANIFEST_PATH
    data = json.loads(p.read_text(encoding="utf-8"))
    validate_organ_manifest(data)
    return data


def manifest_digest(data: dict[str, Any]) -> str:
    organs = data.get("organs", [])
    payload = {"manifest_id": data.get("manifest_id"), "organs": [o.get("organ_id") for o in organs]}
    return compute_record_hash(payload)


def validate_organ_manifest(data: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    organs = data.get("organs", [])
    if not organs:
        failures.append("no organs defined")
    seen: set[str] = set()
    for organ in organs:
        oid = organ.get("organ_id")
        if not oid:
            failures.append("organ missing organ_id")
            continue
        if oid in seen:
            failures.append(f"duplicate organ_id {oid}")
        seen.add(oid)
        for key in ("provider_role", "bus_subscriptions", "bus_publications", "receipt_class"):
            if key not in organ:
                failures.append(f"{oid} missing {key}")
        if organ.get("permission_granted") or organ.get("authority_created"):
            failures.append(f"{oid} grants authority")
        if organ.get("advisory_only") is not True:
            failures.append(f"{oid} must be advisory_only")
    required = [o for o in organs if o.get("required") is True]
    if not any(o.get("organ_id") == "organ:Agent0" for o in organs):
        failures.append("organ:Agent0 missing")
    if failures:
        raise ValueError("; ".join(failures))
    return failures


def boot_plan_receipt(manifest: dict[str, Any], *, run_id: str) -> dict[str, Any]:
    return advisory_payload(
        schema="organ-boot-plan-receipt",
        run_id=run_id,
        manifest_id=manifest.get("manifest_id"),
        manifest_digest=manifest_digest(manifest),
        organ_count=len(manifest.get("organs", [])),
        required_organs=[o["organ_id"] for o in manifest.get("organs", []) if o.get("required")],
    )


__all__ = ["MANIFEST_PATH", "boot_plan_receipt", "load_organ_manifest", "manifest_digest", "validate_organ_manifest"]
