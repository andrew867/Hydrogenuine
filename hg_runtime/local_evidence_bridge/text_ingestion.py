"""LEB-1 bounded local text ingestion."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.local_evidence_bridge.evidence_boundary import validate_source_path
from hg_runtime.local_evidence_bridge.redaction import redact_text
from hg_runtime.local_evidence_bridge.schemas import EvidenceBridgeError, assert_neutral, neutral_flags, record_hash

APPROVED_ROOT = Path("tests/fixtures/local_evidence")
MAX_BYTES = 16_384


def resolve_approved_source(root: Path, relative_path: str) -> Path:
    validate_source_path(relative_path, approved_roots=(str(APPROVED_ROOT).replace("\\", "/"),))
    base = (root / APPROVED_ROOT).resolve()
    resolved = (root / relative_path).resolve()
    if base not in resolved.parents and resolved != base:
        raise EvidenceBridgeError("symlink_or_path_escape_forbidden")
    return resolved


def ingest_text_source(root: Path, relative_path: str, *, source_id: str) -> dict:
    path = resolve_approved_source(root, relative_path)
    raw = path.read_bytes()
    if b"\x00" in raw:
        raise EvidenceBridgeError("binary_file_rejected")
    if len(raw) > MAX_BYTES:
        raise EvidenceBridgeError("oversized_file_rejected")
    text = raw.decode("utf-8")
    redacted, changed = redact_text(text)
    receipt = {
        "schema_version": "1",
        "record_type": "local_evidence_receipt_v1",
        "receipt_id": f"ev-{source_id}",
        "source_id": source_id,
        "source_path": relative_path,
        "source_size_bytes": len(raw),
        "content_hash": record_hash({"content": text}),
        "redacted_text_hash": record_hash({"redacted": redacted}),
        "secret_like_content_redacted": changed,
        "evidence_receipt_is_truth": False,
        "evidence_receipt_is_authority": False,
        "automatic_belief_promotion": False,
        **neutral_flags(),
    }
    receipt["receipt_hash"] = record_hash(receipt)
    assert_neutral(receipt)
    excerpt = {
        "schema_version": "1",
        "record_type": "source_excerpt_receipt_v1",
        "excerpt_id": f"ex-{source_id}",
        "source_id": source_id,
        "excerpt_text_redacted": redacted[:240],
        "excerpt_hash": record_hash({"excerpt": redacted[:240]}),
        "source_excerpt_is_belief": False,
        "automatic_belief_promotion": False,
        **neutral_flags(),
    }
    excerpt["receipt_hash"] = record_hash(excerpt)
    assert_neutral(excerpt)
    redaction = {
        "schema_version": "1",
        "record_type": "evidence_redaction_record_v1",
        "redaction_id": f"red-{source_id}",
        "source_id": source_id,
        "secret_like_content_redacted": changed,
        "secrets_emitted": False,
    }
    redaction["record_hash"] = record_hash(redaction)
    return {"evidence_receipt": receipt, "excerpt_receipt": excerpt, "redaction_record": redaction}
