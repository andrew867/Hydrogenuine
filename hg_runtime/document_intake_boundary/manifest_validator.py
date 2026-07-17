"""DIB manifest entry validation (metadata only)."""

from __future__ import annotations


def validate_manifest_entry(*, entry: dict, manifest: dict) -> dict:
    path = entry.get("manifest_path", "")
    failures: list[str] = []
    if not manifest.get("explicit_manifest_only", True):
        failures.append("explicit_manifest_only_required")
    if path not in manifest.get("allowed_paths", []):
        failures.append("path_not_in_manifest")
    if ".." in path.replace("\\", "/"):
        failures.append("path_traversal")
    if entry.get("symlink_marker"):
        failures.append("symlink_marker")
    if entry.get("directory_crawl_marker") or manifest.get("directory_crawling_enabled"):
        failures.append("directory_crawl")
    return {
        "entry_id": entry.get("file_id", "unknown"),
        "manifest_path": path,
        "valid": not failures,
        "failures": failures,
    }
