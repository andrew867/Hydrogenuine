"""Backup / Restore substrate with schema versioning and sandbox enforcement."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from hg_core.storage_substrate.common import SCHEMA_VERSION, authority_fields, safe_relative_path, sha256_file, stable_hash, utc_now_iso, write_json


class BackupRestoreSubstrate:
    def __init__(self, root: Path):
        self.root = root

    def create_manifest(
        self,
        manifest_id: str,
        source_files: list[Path],
        *,
        proof_index: list[dict[str, Any]] | None = None,
        vector_index_metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        files = {
            str(path): {
                "hash": sha256_file(path),
                "size_bytes": path.stat().st_size,
            }
            for path in sorted(source_files, key=lambda item: str(item))
        }
        manifest = {
            "manifest_id": manifest_id,
            "schema_version": SCHEMA_VERSION,
            "files": files,
            "file_count": len(files),
            "proof_index_snapshot": proof_index or [],
            "vector_index_metadata": vector_index_metadata,
            "restore_is_authority": False,
            "restore_requires_freshness_review": True,
            "created_at": utc_now_iso(),
            **authority_fields(),
        }
        manifest["hash"] = stable_hash(manifest)
        write_json(self.root / f"{manifest_id}.json", manifest)
        return manifest

    def verify_manifest(self, manifest: dict[str, Any]) -> dict[str, Any]:
        mismatches: list[dict[str, str]] = []
        missing: list[str] = []
        for file_path, file_info in manifest.get("files", {}).items():
            path = Path(file_path)
            if not path.exists():
                missing.append(file_path)
                continue
            actual = sha256_file(path)
            if actual != file_info["hash"]:
                mismatches.append({"path": file_path, "expected": file_info["hash"], "actual": actual})
        ok = len(mismatches) == 0 and len(missing) == 0
        return {
            "verified": ok,
            "mismatches": mismatches,
            "missing_files": missing,
            "fails_closed": not ok,
            **authority_fields(),
        }

    def restore_fixture(
        self,
        manifest: dict[str, Any],
        target_name: str,
        *,
        sandbox: bool = True,
    ) -> dict[str, Any]:
        namespace = "sandbox" if sandbox else "production"
        target = safe_relative_path(self.root, f"restore/{namespace}/{target_name}.json")
        receipt = {
            "manifest_id": manifest["manifest_id"],
            "schema_version": manifest.get("schema_version", "unknown"),
            "target": str(target),
            "namespace": namespace,
            "sandbox_only": sandbox,
            "restore_executed": False,
            "restore_authority_created": False,
            "reason": "fixture_restore_plan_only",
            "created_at": utc_now_iso(),
            **authority_fields(),
        }
        receipt["hash"] = stable_hash(receipt)
        write_json(target, receipt)
        return receipt

    def dry_run_restore(self, manifest: dict[str, Any]) -> dict[str, Any]:
        return {
            "manifest_id": manifest["manifest_id"],
            "schema_version": manifest.get("schema_version", "unknown"),
            "file_count": len(manifest.get("files", {})),
            "proof_index_count": len(manifest.get("proof_index_snapshot", [])),
            "dry_run": True,
            "restore_executed": False,
            "target_namespace": "sandbox",
            "reason": "dry_run_restore_plan_only",
            **authority_fields(),
        }
