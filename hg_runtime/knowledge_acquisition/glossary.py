"""Glossary entries. Every entry needs evidence and may never override a domain pack."""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.knowledge_acquisition.schemas import (
    GLOSSARY_ENTRY_SCHEMA,
    KnowledgeAcquisitionError,
    as_list,
    neutral_flags,
    reject_authority_payload,
    reject_forbidden_claim_boundary,
    require_fields,
)


def create_glossary_entry(
    payload: Mapping[str, Any],
    *,
    domain_pack: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    require_fields(payload, ("term", "definition", "evidence_refs"))
    data = dict(payload)
    reject_authority_payload(data)
    reject_forbidden_claim_boundary(data)
    if not as_list(data, "evidence_refs"):
        raise KnowledgeAcquisitionError("glossary_update_requires_evidence")

    # A glossary is acquired knowledge; it is subordinate to the declarative
    # domain pack and can never redefine a pack-locked term or widen a pack.
    if data.get("overrides_domain_pack") or data.get("widens_domain_pack"):
        raise KnowledgeAcquisitionError("glossary_entry_cannot_override_domain_pack")
    if domain_pack is not None:
        locked = set(as_list(domain_pack, "locked_terms"))
        if data["term"] in locked:
            raise KnowledgeAcquisitionError("glossary_entry_cannot_override_domain_pack")

    data.setdefault("schema", GLOSSARY_ENTRY_SCHEMA)
    data.update(neutral_flags())
    return data


__all__ = ["create_glossary_entry"]
