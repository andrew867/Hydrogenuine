"""Proof Artifact Store — read-only proof metadata indexer with hash verification."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from hg_core.storage_substrate.common import authority_fields, sha256_file, stable_hash, utc_now_iso


class ProofArtifactStore:
    """Read-only proof metadata indexer."""

    def __init__(self, workspace: Path):
        self.workspace = workspace

    def index_proof_dir(
        self,
        proof_dir: Path,
        *,
        gate_name: str | None = None,
        verdict: str | None = None,
    ) -> dict[str, Any]:
        proof_dir = proof_dir.resolve()
        files = sorted(path for path in proof_dir.rglob("*") if path.is_file())
        file_hashes = {str(path.relative_to(proof_dir)).replace("\\", "/"): sha256_file(path) for path in files}
        command_log_present = any(name.endswith("command_log.jsonl") for name in file_hashes)
        command_log_path = next((name for name in file_hashes if name.endswith("command_log.jsonl")), None)
        report_path = next((name for name in file_hashes if name.endswith("status.md") or name.endswith("_report.md")), None)
        record: dict[str, Any] = {
            "proof_dir": str(proof_dir),
            "file_hashes": file_hashes,
            "file_count": len(file_hashes),
            "command_log_present": command_log_present,
            "command_log_path": command_log_path,
            "report_path": report_path,
            "gate_name": gate_name,
            "verdict": verdict,
            "indexed_at": utc_now_iso(),
            "proof_is_permission": False,
            **authority_fields(),
        }
        record["hash"] = stable_hash(record)
        return record

    def verify_proof_hashes(self, proof_dir: Path, recorded_hashes: dict[str, str]) -> dict[str, Any]:
        proof_dir = proof_dir.resolve()
        mismatches: list[dict[str, str]] = []
        missing: list[str] = []
        for rel_path, expected_hash in recorded_hashes.items():
            file_path = proof_dir / rel_path
            if not file_path.exists():
                missing.append(rel_path)
                continue
            actual = sha256_file(file_path)
            if actual != expected_hash:
                mismatches.append({"path": rel_path, "expected": expected_hash, "actual": actual})
        ok = len(mismatches) == 0 and len(missing) == 0
        return {
            "verified": ok,
            "mismatches": mismatches,
            "missing_files": missing,
            "fails_closed": not ok,
            "proof_is_permission": False,
            **authority_fields(),
        }

    def missing_proof_receipt(self, proof_ref: str) -> dict[str, Any]:
        return {
            "proof_ref": proof_ref,
            "fails_closed": True,
            "reason": "missing_proof_artifact",
            **authority_fields(),
        }

    def proof_index_receipt(self, proof_records: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "receipt_type": "proof_index",
            "record_count": len(proof_records),
            "records": proof_records,
            "proof_is_permission": False,
            **authority_fields(),
        }
