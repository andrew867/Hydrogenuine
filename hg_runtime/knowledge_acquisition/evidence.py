"""Evidence links binding a claim to a citation and its source."""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.knowledge_acquisition.schemas import (
    EVIDENCE_LINK_SCHEMA,
    neutral_flags,
    reject_authority_payload,
    reject_forbidden_claim_boundary,
    require_fields,
)


def link_evidence(payload: Mapping[str, Any]) -> dict[str, Any]:
    require_fields(payload, ("evidence_id", "claim_id", "citation_id", "source_id"))
    data = dict(payload)
    reject_authority_payload(data)
    reject_forbidden_claim_boundary(data)
    data.setdefault("schema", EVIDENCE_LINK_SCHEMA)
    data.update(neutral_flags())
    return data


__all__ = ["link_evidence"]
