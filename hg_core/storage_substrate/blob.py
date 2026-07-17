"""Blob/Object Artifact Store with artifact classes and manifest."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from hg_core.storage_substrate.common import authority_fields, looks_secret, safe_relative_path, sha256_bytes, stable_hash, utc_now_iso, write_json

ARTIFACT_CLASSES = frozenset({
    "SCREENSHOT_EVIDENCE",
    "OCR_OUTPUT",
    "SENSOR_ARTIFACT",
    "EXPORT",
    "SANDBOX_OUTPUT",
    "MODEL_CACHE",
    "TEMP_CACHE",
    "UNKNOWN_REVIEW_REQUIRED",
})

PROOF_ARTIFACT_CLASSES = frozenset({"SCREENSHOT_EVIDENCE", "SENSOR_ARTIFACT"})
CACHE_ARTIFACT_CLASSES = frozenset({"MODEL_CACHE", "TEMP_CACHE"})

DEFAULT_MAX_BLOB_BYTES = 100 * 1024 * 1024  # 100 MB for tests


class BlobArtifactStore:
    def __init__(self, root: Path, *, max_bytes: int = DEFAULT_MAX_BLOB_BYTES):
        self.root = root
        self.max_bytes = max_bytes
        self._manifest_entries: list[dict[str, Any]] = []

    def put_bytes(
        self,
        name: str,
        data: bytes,
        *,
        mime_type: str = "application/octet-stream",
        retention_class: str = "AUDIT_RETENTION",
        artifact_class: str = "UNKNOWN_REVIEW_REQUIRED",
    ) -> dict[str, Any]:
        source_name = Path(name)
        if source_name.is_absolute() or ".." in source_name.parts:
            raise ValueError(f"path traversal refused: {name}")
        if artifact_class not in ARTIFACT_CLASSES:
            raise ValueError(f"unknown artifact class: {artifact_class}")
        if len(data) > self.max_bytes:
            return {
                "stored": False,
                "reason": "blob_exceeds_size_limit",
                "name": name,
                "size_bytes": len(data),
                "limit_bytes": self.max_bytes,
                **authority_fields(),
            }
        if looks_secret(name) or looks_secret(data.decode("utf-8", errors="ignore")):
            return {
                "stored": False,
                "reason": "secret_like_blob_refused",
                "name": name,
                "quarantine_class": "SECRET_QUARANTINE",
                **authority_fields(),
            }
        digest = sha256_bytes(data)
        hex_digest = digest.split(":", 1)[1]
        relative_path = f"{hex_digest[:2]}/{hex_digest}"
        target = safe_relative_path(self.root, relative_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        metadata = {
            "stored": True,
            "artifact_id": digest,
            "artifact_path": str(target),
            "artifact_hash": digest,
            "source_name": name,
            "mime_type": mime_type,
            "size_bytes": len(data),
            "artifact_class": artifact_class,
            "retention_class": retention_class,
            "created_at": utc_now_iso(),
            **authority_fields(),
        }
        metadata["hash"] = stable_hash(metadata)
        write_json(target.with_suffix(".json"), metadata)
        self._manifest_entries.append(metadata)
        return metadata

    def put_metadata_only(
        self,
        name: str,
        size_bytes: int,
        file_hash: str,
        *,
        artifact_class: str = "UNKNOWN_REVIEW_REQUIRED",
    ) -> dict[str, Any]:
        if artifact_class not in ARTIFACT_CLASSES:
            raise ValueError(f"unknown artifact class: {artifact_class}")
        metadata = {
            "stored": False,
            "metadata_only": True,
            "source_name": name,
            "size_bytes": size_bytes,
            "artifact_hash": file_hash,
            "artifact_class": artifact_class,
            "reason": "large_blob_metadata_without_full_load",
            **authority_fields(),
        }
        metadata["hash"] = stable_hash(metadata)
        return metadata

    def verify_hash(self, name: str, expected_hash: str) -> dict[str, Any]:
        source_name = Path(name)
        if source_name.is_absolute() or ".." in source_name.parts:
            raise ValueError(f"path traversal refused: {name}")
        hex_digest = expected_hash.split(":", 1)[1] if ":" in expected_hash else expected_hash
        target = safe_relative_path(self.root, f"{hex_digest[:2]}/{hex_digest}")
        if not target.exists():
            return {"verified": False, "reason": "blob_not_found", "fails_closed": True, **authority_fields()}
        actual = sha256_bytes(target.read_bytes())
        ok = actual == expected_hash
        return {"verified": ok, "expected": expected_hash, "actual": actual, "fails_closed": not ok, **authority_fields()}

    def emit_manifest(self) -> dict[str, Any]:
        manifest = {
            "manifest_type": "blob_artifact_manifest",
            "entry_count": len(self._manifest_entries),
            "entries": self._manifest_entries,
            "created_at": utc_now_iso(),
            **authority_fields(),
        }
        manifest["hash"] = stable_hash(manifest)
        return manifest
