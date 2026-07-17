"""CT proof bundle schema validation (CT-09 SCH)."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from hg_core.schema_compat.registry import KNOWN_MANIFEST_SCHEMAS

BUNDLE_TIMESTAMP_RE = re.compile(r"^\d{8}T\d{6}Z$")


@dataclass(frozen=True)
class ProofBundleResult:
    bundle_dir: str
    ok: bool
    detail: str
    manifest_schema: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "bundle_dir": self.bundle_dir,
            "ok": self.ok,
            "detail": self.detail,
            "manifest_schema": self.manifest_schema,
        }


def _sha256_file(path: Path) -> str:
    return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"


def validate_ct_proof_bundle_dir(bundle_dir: Path) -> ProofBundleResult:
    rel = str(bundle_dir)
    manifest_path = bundle_dir / "manifest.json"
    gate_path = bundle_dir / "gate_result.json"
    if not manifest_path.exists():
        return ProofBundleResult(rel, False, "missing manifest.json")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return ProofBundleResult(rel, False, f"invalid manifest.json: {exc}")
    schema = manifest.get("schema")
    if schema not in KNOWN_MANIFEST_SCHEMAS:
        return ProofBundleResult(rel, False, f"unknown manifest schema: {schema}", schema)
    required = ("pack", "gate", "timestamp", "head", "path_id", "file_hashes")
    missing = [k for k in required if k not in manifest]
    if missing:
        return ProofBundleResult(rel, False, f"manifest missing keys: {missing}", schema)
    if not gate_path.exists():
        return ProofBundleResult(rel, False, "missing gate_result.json", schema)
    file_hashes = manifest.get("file_hashes", {})
    hash_errors: list[str] = []
    for rel_path, expected in file_hashes.items():
        target = bundle_dir / rel_path
        if not target.exists():
            hash_errors.append(f"missing hashed file: {rel_path}")
            continue
        actual = _sha256_file(target)
        if actual != expected:
            hash_errors.append(f"hash mismatch {rel_path}: {actual} != {expected}")
    if hash_errors:
        return ProofBundleResult(rel, False, "; ".join(hash_errors), schema)
    return ProofBundleResult(rel, True, "manifest and hashes valid", schema)


def scan_ct_proof_bundles(workspace: Path, *, packs: tuple[str, ...] | None = None) -> list[ProofBundleResult]:
    proofs_root = workspace / "docs" / "proofs" / "connective_tissue"
    results: list[ProofBundleResult] = []
    if not proofs_root.exists():
        return results
    pack_dirs = packs or tuple(p.name for p in sorted(proofs_root.iterdir()) if p.is_dir())
    for pack in pack_dirs:
        pack_path = proofs_root / pack
        timestamps = sorted(
            p for p in pack_path.iterdir() if p.is_dir() and BUNDLE_TIMESTAMP_RE.match(p.name)
        )
        if not timestamps:
            results.append(ProofBundleResult(pack, False, "no proof bundles"))
            continue
        latest = timestamps[-1]
        results.append(validate_ct_proof_bundle_dir(latest))
    return results


__all__ = ["ProofBundleResult", "scan_ct_proof_bundles", "validate_ct_proof_bundle_dir"]
