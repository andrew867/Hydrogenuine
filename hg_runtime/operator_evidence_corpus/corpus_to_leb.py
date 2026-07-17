"""Route explicit corpus manifest paths through LEB-style local text ingestion."""

from __future__ import annotations

from pathlib import Path, PurePosixPath

from hg_runtime.local_evidence_bridge.evidence_boundary import validate_source_path
from hg_runtime.local_evidence_bridge.redaction import redact_text
from hg_runtime.local_evidence_bridge.schemas import EvidenceBridgeError, assert_neutral, neutral_flags, record_hash
from hg_runtime.operator_evidence_corpus.schemas import ALLOWED_EXTENSIONS, CORPUS_APPROVED_ROOT

MAX_BYTES = 16_384


def _validate_corpus_path(relative_path: str) -> None:
    validate_source_path(relative_path, approved_roots=(CORPUS_APPROVED_ROOT,))
    suffix = PurePosixPath(relative_path.replace("\\", "/")).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise EvidenceBridgeError("corpus_extension_not_allowed")


def resolve_corpus_source(root: Path, relative_path: str) -> Path:
    _validate_corpus_path(relative_path)
    base = (root / CORPUS_APPROVED_ROOT).resolve()
    resolved = (root / relative_path).resolve()
    if base not in resolved.parents and resolved != base:
        raise EvidenceBridgeError("symlink_or_path_escape_forbidden")
    return resolved


def ingest_corpus_text_source(root: Path, relative_path: str, *, source_id: str) -> dict:
    path = resolve_corpus_source(root, relative_path)
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
        "receipt_id": f"oec-ev-{source_id}",
        "source_id": source_id,
        "source_path": relative_path,
        "source_size_bytes": len(raw),
        "content_hash": record_hash({"content": text}),
        "redacted_text_hash": record_hash({"redacted": redacted}),
        "secret_like_content_redacted": changed,
        "evidence_receipt_is_truth": False,
        "evidence_receipt_is_authority": False,
        "automatic_belief_promotion": False,
        "explicit_corpus_manifest_only": True,
        **neutral_flags(),
    }
    receipt["receipt_hash"] = record_hash(receipt)
    assert_neutral(receipt)
    excerpt = {
        "schema_version": "1",
        "record_type": "source_excerpt_receipt_v1",
        "excerpt_id": f"oec-ex-{source_id}",
        "source_id": source_id,
        "excerpt_text_redacted": redacted[:240],
        "excerpt_hash": record_hash({"excerpt": redacted[:240]}),
        "source_excerpt_is_belief": False,
        "automatic_belief_promotion": False,
        **neutral_flags(),
    }
    excerpt["receipt_hash"] = record_hash(excerpt)
    assert_neutral(excerpt)
    return {"evidence_receipt": receipt, "excerpt_receipt": excerpt}


def build_corpus_local_source_manifest(sources: list[dict], paths: list[str]) -> dict:
    manifest = {
        "schema_version": "1",
        "record_type": "corpus_local_source_manifest_v1",
        "manifest_id": "oec-corpus-local-source-manifest",
        "explicit_source_paths": paths,
        "source_count": len(sources),
        "only_explicit_paths": True,
        "directory_crawling_enabled": False,
        "approved_root": CORPUS_APPROVED_ROOT,
        **neutral_flags(),
    }
    manifest["manifest_hash"] = record_hash(manifest)
    assert_neutral(manifest)
    return manifest
