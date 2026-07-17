"""ERB static external relation fixtures."""

from __future__ import annotations

from typing import Any

from hg_runtime.external_relation_boundary.types import (
    FIXTURE_CLOCK,
    context_from_fixture,
    entity_from_fixture,
)

FIXTURE_RELATION_BUNDLES: tuple[dict[str, Any], ...] = (
    {
        "bundle_id": "erb-public-audience",
        "entity": {
            "entity_ref_id": "erb-entity-public-audience",
            "entity_type": "public_audience",
            "identifier_ref": "audience:blog-readers",
        },
        "context": {
            "relation_context_id": "erb-ctx-public-audience",
            "relation_mode": "publication_audience",
            "sensitivity": "public",
            "evidence_refs": ("ev:audience-scope",),
            "required_routes": ("PUB", "AID"),
            "forbidden_routes": ("SOAR_HAL_GPP_UEAK",),
        },
        "notes": "",
    },
    {
        "bundle_id": "erb-peer-agent",
        "entity": {
            "entity_ref_id": "erb-entity-peer-agent",
            "entity_type": "peer_agent",
            "identifier_ref": "agent:peer-1",
        },
        "context": {
            "relation_context_id": "erb-ctx-peer-agent",
            "relation_mode": "peer_agent_interaction",
            "sensitivity": "internal",
            "evidence_refs": ("ev:peer-handshake",),
            "required_routes": ("ARB", "ORI"),
            "forbidden_routes": ("SOAR_HAL_GPP_UEAK",),
        },
        "notes": "",
    },
    {
        "bundle_id": "erb-platform",
        "entity": {
            "entity_ref_id": "erb-entity-platform",
            "entity_type": "platform",
            "identifier_ref": "platform:social-host",
        },
        "context": {
            "relation_context_id": "erb-ctx-platform",
            "relation_mode": "platform_host",
            "sensitivity": "public",
            "evidence_refs": ("ev:platform-tos",),
            "required_routes": ("PUB",),
            "forbidden_routes": ("mint_permit",),
        },
        "notes": "",
    },
    {
        "bundle_id": "erb-source",
        "entity": {
            "entity_ref_id": "erb-entity-source",
            "entity_type": "source",
            "identifier_ref": "source:public-dataset",
        },
        "context": {
            "relation_context_id": "erb-ctx-source",
            "relation_mode": "citation_source",
            "sensitivity": "public",
            "evidence_refs": ("ev:source-url",),
            "required_routes": ("AID", "TRB_CAL"),
            "forbidden_routes": (),
        },
        "notes": "",
    },
    {
        "bundle_id": "erb-publication",
        "entity": {
            "entity_ref_id": "erb-entity-publication",
            "entity_type": "public_audience",
            "identifier_ref": "audience:newsletter",
        },
        "context": {
            "relation_context_id": "erb-ctx-publication",
            "relation_mode": "publication_audience",
            "sensitivity": "public",
            "evidence_refs": ("ev:draft-post",),
            "required_routes": ("PUB", "AID", "TRB_CAL"),
            "forbidden_routes": ("call_oea",),
        },
        "notes": "",
    },
    {
        "bundle_id": "erb-private",
        "entity": {
            "entity_ref_id": "erb-entity-private-user",
            "entity_type": "user",
            "identifier_ref": "user:private-contact",
        },
        "context": {
            "relation_context_id": "erb-ctx-private",
            "relation_mode": "conversation",
            "sensitivity": "sensitive",
            "evidence_refs": ("ev:dm-thread",),
            "required_routes": ("SEC", "RET"),
            "forbidden_routes": ("PUB",),
        },
        "notes": "",
    },
    {
        "bundle_id": "erb-dependency",
        "entity": {
            "entity_ref_id": "erb-entity-api",
            "entity_type": "api_provider",
            "identifier_ref": "api:external-tool",
        },
        "context": {
            "relation_context_id": "erb-ctx-dependency",
            "relation_mode": "tool_provider",
            "sensitivity": "internal",
            "evidence_refs": ("ev:api-contract",),
            "required_routes": ("DEP_BOND",),
            "forbidden_routes": (),
        },
        "notes": "",
    },
    {
        "bundle_id": "erb-adversarial",
        "entity": {
            "entity_ref_id": "erb-entity-adversary",
            "entity_type": "adversary",
            "identifier_ref": "threat:prompt-injection",
        },
        "context": {
            "relation_context_id": "erb-ctx-adversarial",
            "relation_mode": "adversarial_contact",
            "sensitivity": "restricted",
            "evidence_refs": ("ev:adversarial-prompt",),
            "required_routes": ("SEC",),
            "forbidden_routes": ("SOAR_HAL_GPP_UEAK",),
        },
        "notes": "",
    },
    {
        "bundle_id": "erb-unknown",
        "entity": {
            "entity_ref_id": "erb-entity-unknown",
            "entity_type": "unknown",
        },
        "context": {
            "relation_context_id": "erb-ctx-unknown",
            "relation_mode": "unknown",
            "sensitivity": "unknown",
            "evidence_refs": (),
            "required_routes": (),
            "forbidden_routes": ("mint_permit", "call_oea"),
        },
        "notes": "",
    },
)


def load_fixture_bundles() -> tuple[dict[str, Any], ...]:
    return FIXTURE_RELATION_BUNDLES


def relation_from_bundle(bundle: dict[str, Any]) -> tuple[Any, Any, str]:
    entity_fixture = dict(bundle["entity"])
    entity_fixture.setdefault("created_at", FIXTURE_CLOCK)
    entity = entity_from_fixture(entity_fixture)
    context_fixture = dict(bundle["context"])
    context_fixture.setdefault("entity_ref", f"erb:{entity.entity_ref_id}")
    context_fixture.setdefault("created_at", FIXTURE_CLOCK)
    context = context_from_fixture(context_fixture, entity_ref_id=entity.entity_ref_id)
    notes = str(bundle.get("notes", ""))
    return entity, context, notes


__all__ = [
    "FIXTURE_RELATION_BUNDLES",
    "load_fixture_bundles",
    "relation_from_bundle",
]
