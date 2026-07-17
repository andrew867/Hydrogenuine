"""Workbench artifact references and artifact-hash records.

A benchmark artifact is the work product a case produced. It is not truth on its own:
it must carry a content hash, and that hash must be verified against the recorded
content before any case may count as GREEN. Hashing is never skipped.
"""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.memory_ledger.hash_chain import canonical_hash
from hg_runtime.economic_benchmark.schemas import (
    ARTIFACT_HASH_RECORD_SCHEMA,
    BENCHMARK_ARTIFACT_SCHEMA,
    EconomicBenchmarkError,
    neutral_flags,
    preempt_if_needed,
    reject_authority_payload,
    reject_network_and_credentials,
    require_fields,
)


def record_artifact(payload: Mapping[str, Any], *, allow_network: bool = False, control=None) -> dict[str, Any]:
    preempt_if_needed(control)
    require_fields(payload, ("artifact_id", "case_ref", "content"))
    reject_authority_payload(payload)
    reject_network_and_credentials(payload.get("source_locator"), allow_network=allow_network)
    artifact = {
        "schema": BENCHMARK_ARTIFACT_SCHEMA,
        "artifact_id": payload["artifact_id"],
        "case_ref": payload["case_ref"],
        "workbench_artifact_ref": payload.get("workbench_artifact_ref", ""),
        "content": payload["content"],
        "media_type": payload.get("media_type", "text/plain"),
        "verified": False,
        "advisory_only": True,
        **neutral_flags(),
    }
    artifact["content_hash"] = canonical_hash({"content": artifact["content"], "media_type": artifact["media_type"]})
    return artifact


def record_artifact_hash(artifact: Mapping[str, Any], *, control=None) -> dict[str, Any]:
    preempt_if_needed(control)
    if not artifact.get("content_hash"):
        raise EconomicBenchmarkError("artifact_hash_required")
    record = {
        "schema": ARTIFACT_HASH_RECORD_SCHEMA,
        "artifact_ref": artifact.get("artifact_id"),
        "case_ref": artifact.get("case_ref"),
        "artifact_hash": artifact["content_hash"],
        "verified": False,
        **neutral_flags(),
    }
    record["record_hash"] = canonical_hash(record)
    return record


def verify_artifact_hash(
    artifact: Mapping[str, Any],
    hash_record: Mapping[str, Any],
    *,
    control=None,
) -> dict[str, Any]:
    """Recompute the artifact content hash and compare to the recorded hash."""
    preempt_if_needed(control)
    if not hash_record.get("artifact_hash"):
        raise EconomicBenchmarkError("missing_artifact_hash")
    recomputed = canonical_hash({"content": artifact.get("content"), "media_type": artifact.get("media_type", "text/plain")})
    verified = recomputed == hash_record["artifact_hash"]
    if not verified:
        raise EconomicBenchmarkError("artifact_hash_mismatch")
    out = dict(hash_record)
    out["verified"] = True
    out["recomputed_hash"] = recomputed
    out["record_hash"] = canonical_hash({k: v for k, v in out.items() if k != "record_hash"})
    return out


__all__ = ["record_artifact", "record_artifact_hash", "verify_artifact_hash"]
