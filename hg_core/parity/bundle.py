"""Proof bundle path stamping — refuse unstamped seals (CT-03 PAR)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from hg_core.parity.paths import validate_runtime_path_id


class PathParityError(Exception):
    """Bundle or claim violates path parity rules."""


def require_runtime_path_id(path_id: str | None) -> str:
    try:
        return validate_runtime_path_id(path_id)
    except ValueError as exc:
        raise PathParityError(str(exc)) from exc


def seal_runtime_bundle_manifest(
    *,
    proof_dir: Path,
    path_id: str,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Write runtime_path manifest stub; refuses unstamped path_id."""
    validated = require_runtime_path_id(path_id)
    manifest = {
        "schema": "runtime_proof_bundle_v1",
        "runtime_path_id": validated,
        **(extra or {}),
    }
    (proof_dir / "runtime_path_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return manifest


def validate_bundle_manifest(manifest: dict[str, Any]) -> None:
    """Fail closed if runtime evidence bundle lacks path_id."""
    runtime_path = manifest.get("runtime_path_id") or manifest.get("path_id")
    if manifest.get("schema") == "ct_proof_bundle_v1":
        return  # CT pack bundles use connective_tissue/packXX path_id namespace
    require_runtime_path_id(runtime_path if is_runtime_path(manifest) else None)


def is_runtime_path(manifest: dict[str, Any]) -> bool:
    return manifest.get("schema") in {"runtime_proof_bundle_v1", "runtime_run_summary_v1"}


__all__ = [
    "PathParityError",
    "require_runtime_path_id",
    "seal_runtime_bundle_manifest",
    "validate_bundle_manifest",
]
