"""DIB-3 extraction manifest validation."""

from __future__ import annotations

from hg_runtime.document_intake_boundary.schemas import DIBBoundaryError

EXTRACTION_ALLOWED_CLASSES = {"TEXT_PLAIN_ALLOWED", "MARKDOWN_ALLOWED"}


def validate_extraction_manifest_entry(*, entry: dict, manifest: dict) -> dict:
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
    if entry.get("directory_crawl_marker"):
        failures.append("directory_crawl")
    cls = entry.get("classification_class", "")
    if cls == "JSON_MANIFEST_ALLOWED":
        failures.append("json_manifest_only_not_evidence_extraction")
    elif cls not in EXTRACTION_ALLOWED_CLASSES:
        failures.append("classification_not_allowed_for_extraction")
    return {
        "entry_id": entry.get("file_id", "unknown"),
        "manifest_path": path,
        "valid": not failures,
        "failures": failures,
    }


def assert_extraction_allowed(*, entry: dict, manifest: dict) -> None:
    result = validate_extraction_manifest_entry(entry=entry, manifest=manifest)
    if not result["valid"]:
        raise DIBBoundaryError(result["failures"][0])
