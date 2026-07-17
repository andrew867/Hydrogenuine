"""DIB document file record builder."""

from __future__ import annotations

from hg_runtime.document_intake_boundary.schemas import assert_neutral, neutral_flags, record_hash


def build_document_file_record(
    *,
    file_id: str,
    manifest_path: str,
    filename_label: str,
    size_bytes: int = 0,
    mtime: str = "2026-06-20T00:00:00Z",
    content_fingerprint: str | None = None,
) -> dict:
    fingerprint = content_fingerprint or record_hash(
        {"manifest_path": manifest_path, "file_id": file_id, "size_bytes": size_bytes}
    )
    record = {
        "schema_version": "1",
        "record_type": "document_file_record_v1",
        "file_id": file_id,
        "manifest_path": manifest_path,
        "filename_label": filename_label,
        "size_bytes": size_bytes,
        "mtime": mtime,
        "content_fingerprint": fingerprint,
        "filename_treated_as_source_identity": False,
        "doctrine_note": "Filename is not source identity.",
        **neutral_flags(),
    }
    record["record_hash"] = record_hash(record)
    assert_neutral(record)
    return record
