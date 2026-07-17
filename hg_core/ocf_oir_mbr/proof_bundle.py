"""OCF/OIR/MBR proof bundle adapter."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def sha256_file(path: Path) -> str:
    return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"


def new_proof_dir(workspace: Path, pack: str) -> Path:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return workspace / "docs" / "proofs" / "ocf_oir_mbr" / pack / ts


def emit_proof_bundle(
    proof_dir: Path,
    *,
    pack: str,
    gate: str,
    head: str,
    artifacts: dict[str, Any],
    gate_ok: bool,
) -> dict[str, Any]:
    proof_dir.mkdir(parents=True, exist_ok=True)
    artifacts_dir = proof_dir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    for name, payload in artifacts.items():
        target = artifacts_dir / name
        if isinstance(payload, (dict, list)):
            target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        else:
            target.write_text(str(payload), encoding="utf-8")
    gate_result = {"gate": gate, "ok": gate_ok, "pack": pack, "proof_dir": str(proof_dir)}
    (proof_dir / "gate_result.json").write_text(json.dumps(gate_result, indent=2), encoding="utf-8")
    file_hashes = {"gate_result.json": sha256_file(proof_dir / "gate_result.json")}
    command_log = proof_dir / "command_log.jsonl"
    if command_log.exists():
        file_hashes["command_log.jsonl"] = sha256_file(command_log)
    manifest = {
        "schema": "ct_proof_bundle_v1",
        "pack": pack,
        "gate": gate,
        "timestamp": proof_dir.name,
        "head": head,
        "path_id": f"ocf_oir_mbr/{pack}",
        "file_hashes": file_hashes,
    }
    (proof_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (proof_dir / "status.md").write_text(
        f"# {pack} — {proof_dir.name}\n\n**Verdict:** {'GREEN' if gate_ok else 'RED'}\n**HEAD:** `{head}`\n",
        encoding="utf-8",
    )
    return gate_result


__all__ = ["emit_proof_bundle", "new_proof_dir", "sha256_file"]
