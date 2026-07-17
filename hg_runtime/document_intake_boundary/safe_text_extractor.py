"""DIB-3 safe text and markdown extraction (explicit manifest only)."""

from __future__ import annotations

import json
from pathlib import Path

from hg_runtime.document_intake_boundary.dib_to_leb_adapter import build_dib_to_leb_adapter_record
from hg_runtime.document_intake_boundary.extraction_manifest_validator import assert_extraction_allowed, validate_extraction_manifest_entry
from hg_runtime.document_intake_boundary.intake_records import (
    build_document_provenance_adapter_record,
    build_document_source_identity,
    build_extraction_failure_record,
)
from hg_runtime.document_intake_boundary.redaction import build_document_redaction_record, redact_text
from hg_runtime.document_intake_boundary.schemas import DIBBoundaryError, DIB_APPROVED_FIXTURE_ROOT, assert_neutral, neutral_flags, record_hash
from hg_runtime.document_intake_boundary.text_extraction_receipt import build_text_extraction_receipt

APPROVED_ROOT = Path(DIB_APPROVED_FIXTURE_ROOT)
MAX_BYTES = 16_384
EXCERPT_BOUNDARY_CHARS = 240


def load_extraction_manifest(root: Path, manifest_path: str = "tests/fixtures/document_intake_boundary/safe_text_extraction_manifest.json") -> dict:
    path = (root / manifest_path).resolve()
    base = (root / APPROVED_ROOT).resolve()
    if base not in path.parents and path != base:
        raise DIBBoundaryError("manifest_path_escape_forbidden")
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_fixture_path(root: Path, manifest_path: str, intake_root: str) -> Path:
    normalized = manifest_path.replace("\\", "/")
    if ".." in normalized:
        raise DIBBoundaryError("path_traversal_forbidden")
    base = (root / intake_root).resolve()
    resolved = (root / intake_root / normalized).resolve()
    if base not in resolved.parents and resolved != base:
        raise DIBBoundaryError("path_outside_approved_root")
    if resolved.is_symlink():
        raise DIBBoundaryError("symlink_forbidden")
    return resolved


def extract_safe_text_entry(*, root: Path, entry: dict, manifest: dict, idx: int) -> dict:
    validation = validate_extraction_manifest_entry(entry=entry, manifest=manifest)
    if not validation["valid"]:
        failure_class = validation["failures"][0].upper()
        failure = build_extraction_failure_record(
            failure_id=f"dib3-fail-{idx:03d}",
            file_id=entry["file_id"],
            failure_class=failure_class,
        )
        return {"accepted": False, "failure": failure}

    assert_extraction_allowed(entry=entry, manifest=manifest)
    path = resolve_fixture_path(root, entry["manifest_path"], manifest["intake_root"])
    raw = path.read_bytes()
    if b"\x00" in raw:
        failure = build_extraction_failure_record(
            failure_id=f"dib3-fail-{idx:03d}",
            file_id=entry["file_id"],
            failure_class="BINARY_REJECTED",
        )
        return {"accepted": False, "failure": failure}
    if len(raw) > MAX_BYTES:
        failure = build_extraction_failure_record(
            failure_id=f"dib3-fail-{idx:03d}",
            file_id=entry["file_id"],
            failure_class="OVERSIZED_REJECTED",
        )
        return {"accepted": False, "failure": failure}

    text = raw.decode("utf-8")
    redacted, changed = redact_text(text)
    content_hash = record_hash({"content": text})
    redacted_hash = record_hash({"redacted": redacted})
    excerpt = redacted[:EXCERPT_BOUNDARY_CHARS]
    excerpt_hash = record_hash({"excerpt": excerpt})
    source_id = f"dib3-src-{entry['file_id']}"
    source_identity = build_document_source_identity(
        source_id=source_id,
        manifest_id=manifest["manifest_id"],
        file_id=entry["file_id"],
        content_fingerprint=content_hash,
    )
    receipt = build_text_extraction_receipt(
        receipt_id=f"dib3-receipt-{idx:03d}",
        file_id=entry["file_id"],
        source_id=source_id,
        content_hash=content_hash,
        excerpt_hash=excerpt_hash,
        redacted_text_hash=redacted_hash,
        excerpt_boundary_chars=EXCERPT_BOUNDARY_CHARS,
        classification_class=entry["classification_class"],
    )
    redaction = build_document_redaction_record(
        redaction_id=f"dib3-redact-{idx:03d}",
        file_id=entry["file_id"],
        secret_like_content_redacted=changed,
    )
    provenance = build_document_provenance_adapter_record(
        adapter_id=f"dib3-prov-{idx:03d}",
        source_id=source_id,
    )
    leb_adapter = build_dib_to_leb_adapter_record(
        adapter_id=f"dib3-leb-{idx:03d}",
        source_id=source_id,
        extraction_receipt_id=receipt["receipt_id"],
        content_hash=content_hash,
    )
    return {
        "accepted": True,
        "extraction_receipt": receipt,
        "document_redaction_record": redaction,
        "document_source_identity": source_identity,
        "document_provenance_adapter_record": provenance,
        "dib_to_leb_adapter_record": leb_adapter,
    }


def extract_safe_text_manifest(*, root: Path, manifest: dict) -> dict:
    receipts: list[dict] = []
    failures: list[dict] = []
    redactions: list[dict] = []
    source_identities: list[dict] = []
    provenance_records: list[dict] = []
    leb_adapters: list[dict] = []
    for idx, entry in enumerate(manifest.get("entries", [])):
        result = extract_safe_text_entry(root=root, entry=entry, manifest=manifest, idx=idx)
        if result["accepted"]:
            receipts.append(result["extraction_receipt"])
            redactions.append(result["document_redaction_record"])
            source_identities.append(result["document_source_identity"])
            provenance_records.append(result["document_provenance_adapter_record"])
            leb_adapters.append(result["dib_to_leb_adapter_record"])
        else:
            failures.append(result["failure"])
    manifest_record = {
        "manifest_id": manifest["manifest_id"],
        "entry_count": len(manifest.get("entries", [])),
        "receipt_count": len(receipts),
        "failure_count": len(failures),
        "explicit_manifest_only": True,
        "safe_text_markdown_extraction_enabled_only": True,
        "pdf_ingestion_enabled": False,
        "ocr_ingestion_enabled": False,
        **neutral_flags(),
    }
    manifest_record["manifest_hash"] = record_hash(manifest_record)
    assert_neutral(manifest_record)
    return {
        "safe_text_extraction_manifest": manifest_record,
        "extraction_receipts": receipts,
        "extraction_failure_records": failures,
        "document_redaction_records": redactions,
        "document_source_identity_records": source_identities,
        "document_provenance_adapter_records": provenance_records,
        "dib_to_leb_adapter_records": leb_adapters,
        "accepted_count": len(receipts),
        "rejected_count": len(failures),
    }
