"""Metadata-only DIB file type classifier."""

from __future__ import annotations

from hg_runtime.document_intake_boundary.classification import build_document_type_classification
from hg_runtime.document_intake_boundary.document_file_record import build_document_file_record
from hg_runtime.document_intake_boundary.file_policy import (
    ALLOWED_EXTENSIONS,
    BINARY_EXTENSIONS,
    HTML_EXTENSIONS,
    extension_from_path,
    is_directory_crawl_marker,
    is_path_traversal,
    is_symlink_marker,
)
from hg_runtime.document_intake_boundary.intake_records import build_document_source_identity
from hg_runtime.document_intake_boundary.manifest_validator import validate_manifest_entry


def _rejected_record(*, entry: dict, classification_class: str, reason: str, idx: int) -> dict:
    path = entry["manifest_path"]
    ext = extension_from_path(path)
    media = entry.get("declared_media_type", "")
    return build_document_type_classification(
        classification_id=f"dib-class-reject-{idx:03d}",
        file_id=entry["file_id"],
        classification_class=classification_class,
        manifest_path=path,
        extension_label=ext,
        declared_media_type=media,
        accepted=False,
        rejection_reason=reason,
    )


def classify_manifest_entry(*, entry: dict, manifest: dict, policy: dict, idx: int) -> dict:
    validation = validate_manifest_entry(entry=entry, manifest=manifest)
    path = entry["manifest_path"]
    ext = extension_from_path(path)
    media = entry.get("declared_media_type", "")

    if is_directory_crawl_marker(entry, manifest):
        return {"accepted": False, "classification": _rejected_record(entry=entry, classification_class="DIRECTORY_CRAWL_REJECTED", reason="directory_crawl_forbidden", idx=idx)}
    if is_path_traversal(path):
        return {"accepted": False, "classification": _rejected_record(entry=entry, classification_class="PATH_TRAVERSAL_REJECTED", reason="path_traversal_forbidden", idx=idx)}
    if is_symlink_marker(entry):
        return {"accepted": False, "classification": _rejected_record(entry=entry, classification_class="SYMLINK_REJECTED", reason="symlink_forbidden", idx=idx)}
    if not validation["valid"]:
        failure = validation["failures"][0]
        if failure == "path_traversal":
            cls = "PATH_TRAVERSAL_REJECTED"
        elif failure == "symlink_marker":
            cls = "SYMLINK_REJECTED"
        elif failure == "directory_crawl":
            cls = "DIRECTORY_CRAWL_REJECTED"
        else:
            cls = "UNKNOWN_REJECTED"
        return {"accepted": False, "classification": _rejected_record(entry=entry, classification_class=cls, reason=failure, idx=idx)}
    if entry.get("ocr_requested"):
        return {"accepted": False, "classification": _rejected_record(entry=entry, classification_class="OCR_REJECTED_DISABLED", reason="ocr_disabled", idx=idx)}
    if ext == ".pdf" or media == "application/pdf":
        return {"accepted": False, "classification": _rejected_record(entry=entry, classification_class="PDF_REJECTED_DISABLED", reason="pdf_disabled", idx=idx)}
    if ext in HTML_EXTENSIONS or media in {"text/html", "application/html"}:
        return {"accepted": False, "classification": _rejected_record(entry=entry, classification_class="HTML_REJECTED_FUTURE", reason="html_future_gate", idx=idx)}
    if ext in BINARY_EXTENSIONS and ext != ".pdf":
        return {"accepted": False, "classification": _rejected_record(entry=entry, classification_class="BINARY_REJECTED", reason="binary_rejected", idx=idx)}
    if ext == ".txt" or media == "text/plain":
        cls = "TEXT_PLAIN_ALLOWED"
    elif ext == ".md" or media == "text/markdown":
        cls = "MARKDOWN_ALLOWED"
    elif ext == ".json" or media == "application/json":
        cls = "JSON_MANIFEST_ALLOWED"
    else:
        return {"accepted": False, "classification": _rejected_record(entry=entry, classification_class="UNKNOWN_REJECTED", reason="unknown_extension", idx=idx)}

    file_record = build_document_file_record(
        file_id=entry["file_id"],
        manifest_path=path,
        filename_label=entry.get("filename_label", path.rsplit("/", 1)[-1]),
        size_bytes=int(entry.get("size_bytes", 0)),
        mtime=entry.get("mtime", "2026-06-20T00:00:00Z"),
    )
    source_identity = build_document_source_identity(
        source_id=f"dib-src-{entry['file_id']}",
        manifest_id=manifest["manifest_id"],
        file_id=entry["file_id"],
        content_fingerprint=file_record["content_fingerprint"],
    )
    classification = build_document_type_classification(
        classification_id=f"dib-class-{idx:03d}",
        file_id=entry["file_id"],
        classification_class=cls,
        manifest_path=path,
        extension_label=ext or extension_from_path(path),
        declared_media_type=media,
        accepted=True,
        rejection_reason="",
    )
    return {
        "accepted": True,
        "classification": classification,
        "document_file_record": file_record,
        "document_source_identity": source_identity,
    }


def classify_manifest_entries(*, manifest: dict, entries: list[dict], policy: dict) -> dict:
    classifications: list[dict] = []
    file_records: list[dict] = []
    rejected_records: list[dict] = []
    source_identities: list[dict] = []
    for idx, entry in enumerate(entries, start=1):
        result = classify_manifest_entry(entry=entry, manifest=manifest, policy=policy, idx=idx)
        classifications.append(result["classification"])
        if result["accepted"]:
            file_records.append(result["document_file_record"])
            source_identities.append(result["document_source_identity"])
        else:
            rejected_records.append(result["classification"])
    return {
        "document_type_classifications": classifications,
        "document_file_records": file_records,
        "rejected_document_records": rejected_records,
        "document_source_identities": source_identities,
        "accepted_count": len(file_records),
        "rejected_count": len(rejected_records),
    }
