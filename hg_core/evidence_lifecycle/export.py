"""Export bundles with manifest, hashes, and redaction (CT-10 RET)."""

from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from hg_core.evidence_lifecycle.policy import RetentionPolicy
from hg_core.secrets.redact import redact_payload
from hg_core.secrets.scan import scan_directory


@dataclass(frozen=True)
class ExportResult:
    ok: bool
    export_dir: str
    detail: str
    manifest: dict[str, Any] | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "export_dir": self.export_dir,
            "detail": self.detail,
            "manifest": self.manifest,
        }


def _sha256_file(path: Path) -> str:
    return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"


def export_bundle(
    source_dir: Path,
    dest_dir: Path,
    policy: RetentionPolicy,
    *,
    artifact_class: str,
    sec_scan_applied: bool = False,
) -> ExportResult:
    entry = policy.class_policy(artifact_class)
    if entry is None:
        return ExportResult(False, str(dest_dir), "unknown artifact class")
    if entry.sec_handling_required and not sec_scan_applied:
        hits = scan_directory(source_dir)
        if hits:
            return ExportResult(False, str(dest_dir), "sensitive export requires SEC scan/redaction")
    if entry.redaction_before_export and not sec_scan_applied:
        return ExportResult(False, str(dest_dir), "redaction_before_export required")
    if dest_dir.exists():
        shutil.rmtree(dest_dir)
    shutil.copytree(source_dir, dest_dir)
    if entry.redaction_before_export or entry.sec_handling_required:
        for json_path in dest_dir.rglob("*.json"):
            try:
                data = json.loads(json_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            if isinstance(data, dict):
                json_path.write_text(
                    json.dumps(redact_payload(data), indent=2),
                    encoding="utf-8",
                )
    file_hashes = {
        str(p.relative_to(dest_dir)).replace("\\", "/"): _sha256_file(p)
        for p in sorted(dest_dir.rglob("*"))
        if p.is_file() and p.name != "export_manifest.json"
    }
    manifest: dict[str, Any] = {
        "schema": "evidence_export_v1",
        "artifact_class": artifact_class,
        "source": str(source_dir),
        "file_hashes": file_hashes,
        "sec_scan_applied": sec_scan_applied or entry.sec_handling_required,
        "redaction_applied": entry.redaction_before_export,
    }
    if entry.export_requires_hashes and not file_hashes:
        return ExportResult(False, str(dest_dir), "policy requires file hashes", manifest)
    if not entry.export_requires_manifest:
        return ExportResult(True, str(dest_dir), "export complete without manifest", manifest)
    manifest_path = dest_dir / "export_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    manifest["file_hashes"]["export_manifest.json"] = _sha256_file(manifest_path)
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return ExportResult(True, str(dest_dir), "export complete", manifest)


__all__ = ["ExportResult", "export_bundle"]
