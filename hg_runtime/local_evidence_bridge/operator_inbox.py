"""LEB-4 operator evidence inbox (local-only, disabled by default).

Processes an explicit operator source manifest against an explicit allowed root.
Every entry is either accepted (as a hashed, redacted, non-authoritative source
record) or rejected (with a bounded reason). Nothing is trusted, promoted to
belief, or authorized.

Boundaries enforced here:
- operator inbox disabled by default (explicit enable flag required)
- explicit manifest required (no directory crawling)
- path traversal / absolute path rejected
- out-of-root path rejected
- symlink escape rejected
- disallowed extension (e.g. .pdf, .bin) rejected
- binary content (NUL byte) rejected
- oversized file rejected (bounded by policy.max_bytes)
- links are not followed; web is not accessed; providers are not called
"""

from __future__ import annotations

from pathlib import Path

from hg_runtime.local_evidence_bridge.path_policy import (
    extension_allowed,
    resolve_inbox_path,
)
from hg_runtime.local_evidence_bridge.inbox_manifest import validate_inbox_manifest
from hg_runtime.local_evidence_bridge.redaction import redact_text
from hg_runtime.local_evidence_bridge.schemas import (
    EvidenceBridgeError,
    assert_neutral,
    neutral_flags,
    record_hash,
)


def _accepted_record(*, source_id: str, relative_path: str, raw: bytes, redacted: str, changed: bool) -> dict:
    record = {
        "schema_version": "1",
        "record_type": "accepted_source_record_v1",
        "source_id": source_id,
        "source_path": relative_path,
        "source_size_bytes": len(raw),
        "content_hash": record_hash({"content": raw.decode("utf-8")}),
        "redacted_text_hash": record_hash({"redacted": redacted}),
        "excerpt_text_redacted": redacted[:240],
        "secret_like_content_redacted": changed,
        "accepted_via_explicit_manifest": True,
        "accepted_source_is_truth": False,
        "accepted_source_is_belief": False,
        "accepted_source_is_authority": False,
        "local_file_trusted_by_default": False,
        "links_followed": False,
        **neutral_flags(),
    }
    record["record_hash"] = record_hash(record)
    assert_neutral(record)
    return record


def _rejected_record(*, source_id: str, relative_path: str, reason: str) -> dict:
    record = {
        "schema_version": "1",
        "record_type": "rejected_source_record_v1",
        "source_id": source_id,
        "source_path": relative_path,
        "rejection_reason": reason,
        "accepted": False,
        "links_followed": False,
        **neutral_flags(),
    }
    record["record_hash"] = record_hash(record)
    assert_neutral(record)
    return record


def _classify_entry(root: Path, entry: dict, policy: dict) -> dict:
    source_id = entry["source_id"]
    relative_path = entry["relative_path"]
    allowed_root = policy["allowed_root"]
    max_bytes = policy["max_bytes"]

    if not policy.get("operator_inbox_enabled"):
        return _rejected_record(source_id=source_id, relative_path=relative_path, reason="operator_inbox_disabled")

    # Path policy: traversal / absolute / out-of-root / symlink escape.
    try:
        resolved = resolve_inbox_path(root, relative_path, allowed_root)
    except EvidenceBridgeError as exc:
        return _rejected_record(source_id=source_id, relative_path=relative_path, reason=str(exc))

    if not extension_allowed(relative_path):
        suffix = relative_path.lower()
        reason = "pdf_rejected" if suffix.endswith(".pdf") else "disallowed_extension_rejected"
        return _rejected_record(source_id=source_id, relative_path=relative_path, reason=reason)

    if not resolved.exists() or not resolved.is_file():
        return _rejected_record(source_id=source_id, relative_path=relative_path, reason="source_file_missing")

    raw = resolved.read_bytes()
    if b"\x00" in raw:
        return _rejected_record(source_id=source_id, relative_path=relative_path, reason="binary_content_rejected")
    if len(raw) > max_bytes:
        return _rejected_record(source_id=source_id, relative_path=relative_path, reason="oversized_file_rejected")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return _rejected_record(source_id=source_id, relative_path=relative_path, reason="binary_content_rejected")

    redacted, changed = redact_text(text)
    return _accepted_record(source_id=source_id, relative_path=relative_path, raw=raw, redacted=redacted, changed=changed)


def process_inbox(root: Path, policy: dict, manifest: dict) -> dict:
    """Process the operator manifest into accepted/rejected source records."""
    validate_inbox_manifest(manifest)
    records = [_classify_entry(root, entry, policy) for entry in manifest["entries"]]
    accepted = sorted(
        (r for r in records if r["record_type"] == "accepted_source_record_v1"),
        key=lambda r: r["source_id"],
    )
    rejected = sorted(
        (r for r in records if r["record_type"] == "rejected_source_record_v1"),
        key=lambda r: r["source_id"],
    )
    return {"accepted": accepted, "rejected": rejected}
