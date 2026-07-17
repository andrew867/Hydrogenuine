"""SQP-1 source identity and fingerprint builder."""

from __future__ import annotations

from hg_runtime.source_quality_provenance.hashing import record_hash
from hg_runtime.source_quality_provenance.source_fingerprint import build_source_fingerprint
from hg_runtime.source_quality_provenance.source_identity import build_source_identity
from hg_runtime.source_quality_provenance.source_normalizer import normalize_source_text


def build_fingerprint_bundle(source: dict) -> dict:
    """Build SQP identity/fingerprint records from an explicit fixture source."""

    source_id = source["source_id"]
    normalized_text = normalize_source_text(source["text"])
    content_hash = record_hash({"text": source["text"]})
    normalized_hash = record_hash({"normalized_text": normalized_text})
    envelope_hash = record_hash(
        {
            "path_ref": source["path_ref"],
            "source_key": source["logical_source_key"],
            "excerpt_id": source.get("excerpt_id"),
        }
    )
    identity = build_source_identity(
        source_id=source_id,
        logical_source_key=source["logical_source_key"],
        path_ref=source["path_ref"],
        envelope_ref=source.get("envelope_ref", "LEB-1-TEXT-EVIDENCE-INGESTION"),
    )
    fingerprint = build_source_fingerprint(source_id=source_id, content_hash=content_hash, envelope_hash=envelope_hash)
    fingerprint["normalized_text_hash"] = normalized_hash
    fingerprint["source_path_ref"] = source["path_ref"]
    fingerprint["logical_source_key"] = source["logical_source_key"]
    fingerprint["excerpt_id"] = source.get("excerpt_id")
    fingerprint["fingerprint_hash"] = record_hash(fingerprint)
    return {"identity": identity, "fingerprint": fingerprint, "normalized_text": normalized_text}
