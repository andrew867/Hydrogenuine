"""ORI static fixture review requests — OPB/IPB/ARB/EGI intake only."""

from __future__ import annotations

from typing import Any

from hg_runtime.operator_review_intake.request_types import review_request_from_fixture

FIXTURE_REVIEW_REQUESTS: tuple[dict[str, Any], ...] = (
    {
        "review_request_id": "ori-req-opb-shutdown",
        "source_module": "OPB",
        "source_ref": "opb:shutdown-packet-1",
        "review_type": "shutdown_or_reset",
        "summary": "Operator shutdown request with irreversible effects",
        "urgency": "critical",
        "reversibility": "irreversible",
        "requires_explicit_operator_action": True,
        "silence_policy": "silence_is_no",
        "evidence_refs": ["evidence:opb-shutdown-1"],
    },
    {
        "review_request_id": "ori-req-ipb-clarify",
        "source_module": "IPB",
        "source_ref": "ipb:envelope-clarify-1",
        "review_type": "clarification",
        "summary": "Clarify local autonomy envelope boundary",
        "urgency": "medium",
        "reversibility": "reversible",
        "requires_explicit_operator_action": False,
        "silence_policy": "silence_is_defer",
        "evidence_refs": ["evidence:ipb-clarify-1"],
    },
    {
        "review_request_id": "ori-req-ipb-clarify-dup",
        "source_module": "IPB",
        "source_ref": "ipb:envelope-clarify-2",
        "review_type": "clarification",
        "summary": "Clarify local autonomy envelope boundary",
        "urgency": "medium",
        "reversibility": "reversible",
        "requires_explicit_operator_action": False,
        "silence_policy": "silence_is_defer",
        "evidence_refs": ["evidence:ipb-clarify-2"],
    },
    {
        "review_request_id": "ori-req-arb-route",
        "source_module": "ARB",
        "source_ref": "arb:route-conflict-1",
        "review_type": "route_conflict",
        "summary": "Repeated route conflict requires operator choice",
        "urgency": "high",
        "reversibility": "partially_reversible",
        "requires_explicit_operator_action": True,
        "silence_policy": "silence_requires_escalation",
        "evidence_refs": ["evidence:arb-route-1"],
    },
    {
        "review_request_id": "ori-req-egi-infra",
        "source_module": "EGI",
        "source_ref": "egi:infra-proposal-1",
        "review_type": "infrastructure_request",
        "summary": "Ordinary EGI infrastructure proposal packet",
        "urgency": "medium",
        "reversibility": "reversible",
        "requires_explicit_operator_action": True,
        "silence_policy": "silence_is_no",
        "evidence_refs": ["evidence:egi-infra-1"],
    },
    {
        "review_request_id": "ori-req-egi-infra-dup",
        "source_module": "EGI",
        "source_ref": "egi:infra-proposal-2",
        "review_type": "infrastructure_request",
        "summary": "Ordinary EGI infrastructure proposal packet",
        "urgency": "medium",
        "reversibility": "reversible",
        "requires_explicit_operator_action": True,
        "silence_policy": "silence_is_no",
        "evidence_refs": ["evidence:egi-infra-2"],
    },
    {
        "review_request_id": "ori-req-low-digest-a",
        "source_module": "ARB",
        "source_ref": "arb:observation-1",
        "review_type": "route_conflict",
        "summary": "Informational repeated nonurgent route conflict",
        "urgency": "low",
        "reversibility": "reversible",
        "requires_explicit_operator_action": False,
        "silence_policy": "silence_is_defer",
        "evidence_refs": ["evidence:arb-low-1"],
    },
    {
        "review_request_id": "ori-req-low-digest-b",
        "source_module": "ARB",
        "source_ref": "arb:observation-2",
        "review_type": "route_conflict",
        "summary": "Digestable observation for operator inbox",
        "urgency": "low",
        "reversibility": "reversible",
        "requires_explicit_operator_action": False,
        "silence_policy": "silence_is_defer",
        "evidence_refs": ["evidence:arb-low-2"],
    },
)


def load_static_fixture_requests() -> tuple[Any, ...]:
    return tuple(review_request_from_fixture(row) for row in FIXTURE_REVIEW_REQUESTS)


def fixture_requests_for_sources(*sources: str) -> tuple[Any, ...]:
    return tuple(
        review_request_from_fixture(row)
        for row in FIXTURE_REVIEW_REQUESTS
        if row["source_module"] in sources
    )


__all__ = [
    "FIXTURE_REVIEW_REQUESTS",
    "fixture_requests_for_sources",
    "load_static_fixture_requests",
]
