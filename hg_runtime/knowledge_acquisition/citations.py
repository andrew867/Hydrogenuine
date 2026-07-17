"""Source citation records. A citation must point to a locatable place in a source."""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.knowledge_acquisition.schemas import (
    SOURCE_CITATION_SCHEMA,
    KnowledgeAcquisitionError,
    neutral_flags,
    reject_authority_payload,
    reject_forbidden_claim_boundary,
    require_fields,
)


def create_citation(payload: Mapping[str, Any]) -> dict[str, Any]:
    require_fields(payload, ("citation_id", "source_id", "locator", "excerpt"))
    data = dict(payload)
    reject_authority_payload(data)
    reject_forbidden_claim_boundary(data)
    if not str(data.get("locator") or "").strip():
        raise KnowledgeAcquisitionError("source_citation_requires_locator")
    data.setdefault("schema", SOURCE_CITATION_SCHEMA)
    data.update(neutral_flags())
    return data


__all__ = ["create_citation"]
