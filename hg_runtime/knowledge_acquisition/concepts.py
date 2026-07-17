"""Concept extraction records derived from cited sources."""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.knowledge_acquisition.schemas import (
    CONCEPT_RECORD_SCHEMA,
    KnowledgeAcquisitionError,
    as_list,
    neutral_flags,
    reject_authority_payload,
    reject_forbidden_claim_boundary,
    require_fields,
)


def extract_concept(payload: Mapping[str, Any]) -> dict[str, Any]:
    require_fields(payload, ("concept_id", "term", "definition", "source_refs"))
    data = dict(payload)
    reject_authority_payload(data)
    reject_forbidden_claim_boundary(data)
    if not as_list(data, "source_refs"):
        raise KnowledgeAcquisitionError("concept_requires_source_refs")
    data.setdefault("schema", CONCEPT_RECORD_SCHEMA)
    data.update(neutral_flags())
    return data


__all__ = ["extract_concept"]
