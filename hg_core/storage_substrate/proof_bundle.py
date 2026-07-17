"""Proof bundle helpers for storage substrate gates."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hg_core.storage_substrate.common import environment_info, sha256_file, write_json


def new_proof_dir(workspace: Path, pack: str) -> Path:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return workspace / "docs" / "proofs" / "storage_artifact_vector" / pack / ts


def emit_proof_bundle(
    workspace: Path,
    proof_dir: Path,
    *,
    pack: str,
    gate: str,
    artifacts: dict[str, Any],
    gate_ok: bool,
) -> dict[str, Any]:
    proof_dir.mkdir(parents=True, exist_ok=True)
    artifacts_dir = proof_dir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    for name, payload in artifacts.items():
        target = artifacts_dir / name
        if isinstance(payload, (dict, list)):
            write_json(target, payload)
        else:
            target.write_text(str(payload), encoding="utf-8")

    gate_result = {
        "gate": gate,
        "ok": gate_ok,
        "pack": pack,
        "proof_dir": str(proof_dir),
        "permission_granted": False,
        "authority_created": False,
        "authority_conversion": False,
    }
    write_json(proof_dir / "gate_result.json", gate_result)

    file_hashes: dict[str, str] = {}
    for path in sorted(proof_dir.rglob("*")):
        if path.is_file():
            file_hashes[str(path.relative_to(proof_dir)).replace("\\", "/")] = sha256_file(path)

    manifest = {
        "schema": "storage_artifact_vector_proof_bundle_v1",
        "pack": pack,
        "gate": gate,
        "timestamp": proof_dir.name,
        "environment": environment_info(workspace),
        "path_id": f"storage_artifact_vector/{pack}",
        "file_hashes": file_hashes,
        "permission_granted": False,
        "authority_created": False,
        "authority_conversion": False,
    }
    write_json(proof_dir / "manifest.json", manifest)
    (proof_dir / "status.md").write_text(
        f"# {pack} - {proof_dir.name}\n\n**Verdict:** {'GREEN' if gate_ok else 'RED'}\n",
        encoding="utf-8",
    )
    return gate_result


__all__ = ["emit_proof_bundle", "new_proof_dir"]

