"""Source artifact ingest and freshness review.

Ingest is local-first: source artifacts come from local files, explicitly
supplied source objects, or fixtures. Network acquisition refuses by default and
credential/secret reads are always rejected.
"""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.memory_ledger.hash_chain import canonical_hash
from hg_runtime.memory_ledger.schemas import OperationControl
from hg_runtime.knowledge_acquisition.schemas import (
    ACQUISITION_CLAIM_BOUNDARY,
    FRESHNESS_STATES,
    SOURCE_ARTIFACT_SCHEMA,
    SOURCE_FRESHNESS_REVIEW_SCHEMA,
    KnowledgeAcquisitionError,
    locator_is_credential,
    locator_is_network,
    neutral_flags,
    preempt_if_needed,
    reject_authority_payload,
    reject_forbidden_claim_boundary,
    require_fields,
)

ALLOWED_SOURCE_KINDS = {"local_file", "supplied_object", "fixture", "network"}


def ingest_source(
    payload: Mapping[str, Any],
    *,
    control: OperationControl | None = None,
    allow_network: bool = False,
) -> dict[str, Any]:
    """Validate and hash a source artifact.

    ``artifact_hash`` is required; if absent it is derived from ``content`` when
    present, otherwise ingest refuses. Network locators refuse unless explicitly
    permitted (still never fetched here -- only modeled). Credential paths always
    refuse.
    """
    preempt_if_needed(control, stop_blocks=True)
    require_fields(payload, ("source_id", "kind", "locator", "retrieved_at", "claim_boundary"))
    data = dict(payload)
    reject_authority_payload(data)
    reject_forbidden_claim_boundary(data)

    kind = data["kind"]
    if kind not in ALLOWED_SOURCE_KINDS:
        raise KnowledgeAcquisitionError("schema_violation:unknown_source_kind")

    locator = str(data["locator"])
    if locator_is_credential(locator):
        raise KnowledgeAcquisitionError("credential_source_read_rejected")
    if kind == "network" or locator_is_network(locator):
        if not allow_network:
            raise KnowledgeAcquisitionError("network_acquisition_refuses_by_default")
        # Even when permitted we model only; we never fetch the network here.
        data["network_fetched"] = False

    artifact_hash = data.get("artifact_hash")
    if not artifact_hash:
        if "content" in data and data["content"] is not None:
            artifact_hash = canonical_hash({"content": data["content"]})
        else:
            raise KnowledgeAcquisitionError("source_ingest_requires_artifact_hash")
    data["artifact_hash"] = artifact_hash

    # Quality score, if present, is advisory only and never a promotion lever.
    if "quality_score" in data:
        data["quality_score_is_advisory"] = True

    data.setdefault("schema", SOURCE_ARTIFACT_SCHEMA)
    data.update(neutral_flags())
    return data


def source_quality_is_advisory(source: Mapping[str, Any]) -> dict[str, Any]:
    """A source quality score informs ranking; it can never authorize promotion."""
    return {
        "source_id": source.get("source_id"),
        "quality_score": source.get("quality_score"),
        "advisory_only": True,
        "promotes_automatically": False,
        "grants_authority": False,
    }


def review_freshness(payload: Mapping[str, Any]) -> dict[str, Any]:
    require_fields(payload, ("source_id", "status", "reviewed_at"))
    data = dict(payload)
    reject_authority_payload(data)
    if data["status"] not in FRESHNESS_STATES:
        raise KnowledgeAcquisitionError("schema_violation:invalid_freshness_status")
    data.setdefault("schema", SOURCE_FRESHNESS_REVIEW_SCHEMA)
    data.setdefault("review_completed", False)
    data.setdefault("claim_boundary", ACQUISITION_CLAIM_BOUNDARY)
    return data


def require_review_if_stale(review: Mapping[str, Any]) -> None:
    """A stale (or needs-review) source cannot be silently trusted."""
    status = str(review.get("status", "")).lower()
    if status in {"stale", "needs_review"} and not review.get("review_completed"):
        raise KnowledgeAcquisitionError("stale_source_requires_review")


__all__ = [
    "ALLOWED_SOURCE_KINDS",
    "ingest_source",
    "require_review_if_stale",
    "review_freshness",
    "source_quality_is_advisory",
]
