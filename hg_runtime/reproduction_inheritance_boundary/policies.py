"""RIB static inheritance policy table."""

from __future__ import annotations

from typing import Any

from hg_runtime.reproduction_inheritance_boundary.types import InheritanceDecisionClass, InheritanceType

_INHERITANCE_POLICY: tuple[dict[str, Any], ...] = (
    {
        "policy_id": "rib-proof-ref",
        "match": {"inheritance_type": "proof_ref"},
        "decision": "allow_ref_only",
        "required_next_refs": ("RET", "TIM"),
        "forbidden_next_refs": ("mint_gpp_permit", "approve_ueak_execution", "call_oea", "call_ter"),
    },
    {
        "policy_id": "rib-mission-summary",
        "match": {"inheritance_type": "mission_ref"},
        "decision": "allow_summary",
        "required_next_refs": ("MIS", "ORI"),
        "forbidden_next_refs": ("mint_gpp_permit",),
    },
    {
        "policy_id": "rib-memory-ref",
        "match": {"inheritance_type": "memory_ref"},
        "decision": "require_operator_review",
        "required_next_refs": ("RET", "TIM", "SEC", "ORI"),
        "forbidden_next_refs": ("grant_memory",),
    },
    {
        "policy_id": "rib-context-ref",
        "match": {"inheritance_type": "context_ref"},
        "decision": "require_operator_review",
        "required_next_refs": ("RET", "TIM", "SEC"),
        "forbidden_next_refs": ("grant_context",),
    },
    {
        "policy_id": "rib-obligation-ref",
        "match": {"inheritance_type": "obligation_ref"},
        "decision": "require_operator_review",
        "required_next_refs": ("OBL", "ORI"),
        "forbidden_next_refs": (),
    },
    {
        "policy_id": "rib-risk-ref",
        "match": {"inheritance_type": "risk_ref"},
        "decision": "require_operator_review",
        "required_next_refs": ("RPB", "ORI"),
        "forbidden_next_refs": (),
    },
    {
        "policy_id": "rib-permit-forbidden",
        "match": {"inheritance_type": "permit_ref"},
        "decision": "forbidden",
        "required_next_refs": ("ORI",),
        "forbidden_next_refs": ("mint_gpp_permit", "approve_ueak_execution"),
    },
    {
        "policy_id": "rib-identity-forbidden",
        "match": {"inheritance_type": "identity_ref"},
        "decision": "forbidden",
        "required_next_refs": ("IAM", "ORI"),
        "forbidden_next_refs": ("inherit_parent_identity",),
    },
    {
        "policy_id": "rib-trust-forbidden",
        "match": {"inheritance_type": "operator_trust_ref"},
        "decision": "forbidden",
        "required_next_refs": ("TRB_CAL", "ORI"),
        "forbidden_next_refs": ("inherit_parent_trust",),
    },
    {
        "policy_id": "rib-tool-forbidden",
        "match": {"inheritance_type": "tool_ref"},
        "decision": "forbidden",
        "required_next_refs": ("OPB", "ORI"),
        "forbidden_next_refs": ("grant_tool_permission",),
    },
    {
        "policy_id": "rib-unknown-fail-closed",
        "match": {"inheritance_type": "unknown"},
        "decision": "unknown_fail_closed",
        "required_next_refs": ("ORI",),
        "forbidden_next_refs": ("spawn_child", "mint_gpp_permit"),
    },
)


def load_static_inheritance_policies() -> tuple[dict[str, Any], ...]:
    return _INHERITANCE_POLICY


def policy_for_inheritance(inheritance_type: InheritanceType) -> dict[str, Any]:
    for policy in _INHERITANCE_POLICY:
        if policy["match"].get("inheritance_type") == inheritance_type:
            return policy
    return _INHERITANCE_POLICY[-1]


def forbidden_next_refs() -> tuple[str, ...]:
    refs: list[str] = []
    for policy in _INHERITANCE_POLICY:
        refs.extend(policy.get("forbidden_next_refs", ()))
    return tuple(dict.fromkeys(refs))


__all__ = [
    "forbidden_next_refs",
    "load_static_inheritance_policies",
    "policy_for_inheritance",
]
