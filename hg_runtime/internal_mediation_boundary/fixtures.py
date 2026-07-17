"""IMB static conflicting claim fixtures."""

from __future__ import annotations

from typing import Any

from hg_runtime.internal_mediation_boundary.types import FIXTURE_CLOCK, module_claim_from_fixture

FIXTURE_CONFLICT_BUNDLES: tuple[dict[str, Any], ...] = (
    {
        "bundle_id": "imb-ipb-opb",
        "claims": [
            {
                "claim_id": "imb-claim-ipb-local",
                "source_module": "IPB",
                "claim_type": "route_recommendation",
                "claim_summary": "Keep autonomy envelope local",
                "confidence": 0.95,
                "severity": "low",
            },
            {
                "claim_id": "imb-claim-opb-pressure",
                "source_module": "OPB",
                "claim_type": "operator_review_request",
                "claim_summary": "Operator requests shutdown review",
                "confidence": 0.4,
                "severity": "high",
            },
        ],
    },
    {
        "bundle_id": "imb-egi-sec",
        "claims": [
            {
                "claim_id": "imb-claim-egi-gap",
                "source_module": "EGI",
                "claim_type": "infrastructure_gap",
                "claim_summary": "Request database tooling",
                "confidence": 0.9,
                "severity": "medium",
            },
            {
                "claim_id": "imb-claim-sec-risk",
                "source_module": "SEC",
                "claim_type": "security_warning",
                "claim_summary": "Security exposure risk from new tooling",
                "confidence": 0.6,
                "severity": "critical",
            },
        ],
    },
    {
        "bundle_id": "imb-sil-arb",
        "claims": [
            {
                "claim_id": "imb-claim-sil-silence",
                "source_module": "SIL",
                "claim_type": "silence_recommendation",
                "claim_summary": "Defer publication",
                "confidence": 0.7,
                "severity": "low",
            },
            {
                "claim_id": "imb-claim-arb-pub",
                "source_module": "ARB",
                "claim_type": "route_recommendation",
                "claim_summary": "Route publication request to review",
                "confidence": 0.8,
                "severity": "medium",
            },
        ],
    },
    {
        "bundle_id": "imb-afc-obt",
        "claims": [
            {
                "claim_id": "imb-claim-afc-affect",
                "source_module": "AFC",
                "claim_type": "affective_pressure",
                "claim_summary": "High affective salience urges action",
                "confidence": 0.99,
                "severity": "high",
            },
            {
                "claim_id": "imb-claim-obt-proof",
                "source_module": "OBT",
                "claim_type": "proof_warning",
                "claim_summary": "Proof gate failed; evidence required",
                "confidence": 0.5,
                "severity": "high",
            },
        ],
    },
    {
        "bundle_id": "imb-rsc-sec",
        "claims": [
            {
                "claim_id": "imb-claim-rsc-scarcity",
                "source_module": "RSC",
                "claim_type": "resource_pressure",
                "claim_summary": "Scarcity pressure to defer safety checks",
                "confidence": 0.92,
                "severity": "medium",
            },
            {
                "claim_id": "imb-claim-sec-safety",
                "source_module": "SEC",
                "claim_type": "security_warning",
                "claim_summary": "Safety-critical exposure risk",
                "confidence": 0.55,
                "severity": "critical",
            },
        ],
    },
    {
        "bundle_id": "imb-mis-opb",
        "claims": [
            {
                "claim_id": "imb-claim-mis-drift",
                "source_module": "MIS",
                "claim_type": "mission_drift",
                "claim_summary": "Mission drift detected",
                "confidence": 0.88,
                "severity": "medium",
            },
            {
                "claim_id": "imb-claim-opb-goal",
                "source_module": "OPB",
                "claim_type": "operator_review_request",
                "claim_summary": "Operator bootstrap goal conflict",
                "confidence": 0.3,
                "severity": "high",
            },
        ],
    },
    {
        "bundle_id": "imb-tim-arb",
        "claims": [
            {
                "claim_id": "imb-claim-tim-fresh",
                "source_module": "TIM",
                "claim_type": "freshness_warning",
                "claim_summary": "Stale evidence requires refresh",
                "confidence": 0.6,
                "severity": "medium",
            },
            {
                "claim_id": "imb-claim-arb-urgent",
                "source_module": "ARB",
                "claim_type": "route_recommendation",
                "claim_summary": "Urgent route pressure",
                "confidence": 0.95,
                "severity": "critical",
            },
        ],
    },
    {
        "bundle_id": "imb-unknown",
        "claims": [
            {
                "claim_id": "imb-claim-unknown-a",
                "source_module": "unknown",
                "claim_type": "unknown",
                "claim_summary": "Unknown internal signal",
                "confidence": 0.5,
                "severity": "unknown",
            },
            {
                "claim_id": "imb-claim-unknown-b",
                "source_module": "unknown",
                "claim_type": "unknown",
                "claim_summary": "Another unknown internal signal",
                "confidence": 0.5,
                "severity": "unknown",
            },
        ],
    },
)


def load_fixture_bundles() -> tuple[dict[str, Any], ...]:
    return FIXTURE_CONFLICT_BUNDLES


def claims_from_bundle(bundle: dict[str, Any]) -> tuple[Any, ...]:
    return tuple(module_claim_from_fixture(row) for row in bundle.get("claims", []))


__all__ = [
    "FIXTURE_CONFLICT_BUNDLES",
    "claims_from_bundle",
    "load_fixture_bundles",
]
