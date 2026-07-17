"""LEB-4 operator inbox manifest.

An explicit operator source manifest is REQUIRED before any inbox file is
considered. There is no directory crawling: only the exact relative paths listed
here are eligible, and each must still pass the path policy and content checks.
"""

from __future__ import annotations

from hg_runtime.local_evidence_bridge.schemas import (
    EvidenceBridgeError,
    assert_neutral,
    neutral_flags,
    record_hash,
)


def build_inbox_manifest(*, allowed_root: str, entries: list[dict]) -> dict:
    """Build an operator_source_manifest_v1 from explicit operator entries.

    Each entry is a dict with at least {"relative_path": str, "source_id": str}.
    """
    if not entries:
        raise EvidenceBridgeError("explicit_source_manifest_required")
    normalized = [
        {
            "source_id": e["source_id"],
            "relative_path": e["relative_path"].replace("\\", "/"),
            "declared_by": e.get("declared_by", "operator_fixture"),
        }
        for e in entries
    ]
    manifest = {
        "schema_version": "1",
        "record_type": "operator_source_manifest_v1",
        "manifest_id": "leb4-operator-source-manifest",
        "allowed_root": allowed_root.replace("\\", "/"),
        "entry_count": len(normalized),
        "entries": normalized,
        "explicit_manifest_required": True,
        "directory_crawling_enabled": False,
        "operator_manifest_is_truth": False,
        "operator_manifest_is_authority": False,
        **neutral_flags(),
    }
    manifest["manifest_hash"] = record_hash(manifest)
    assert_neutral(manifest)
    return manifest


def validate_inbox_manifest(manifest: dict) -> None:
    if manifest.get("record_type") != "operator_source_manifest_v1":
        raise EvidenceBridgeError("operator_source_manifest_required")
    if not manifest.get("entries"):
        raise EvidenceBridgeError("explicit_source_manifest_required")
    if manifest.get("directory_crawling_enabled"):
        raise EvidenceBridgeError("directory_crawling_forbidden")
