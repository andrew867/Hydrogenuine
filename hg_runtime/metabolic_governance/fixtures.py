"""MET static metabolic governance fixtures — proposal surfaces and adversarial cases."""

from __future__ import annotations

from typing import Any

from hg_runtime.metabolic_governance.types import FIXTURE_CLOCK, REQUIRED_METABOLIC_ORGANS

_BASE_ORGAN_RECEIPTS: tuple[dict[str, Any], ...] = (
    {
        "receipt_id": "met:mod-brb",
        "organ": "BRB",
        "module": "breathing_regulation_boundary",
        "status": "completed",
        "completed_at": FIXTURE_CLOCK,
        "payload_ref": "brb:cadence-observe",
    },
    {
        "receipt_id": "met:mod-nib",
        "organ": "NIB",
        "module": "nutrient_intake_boundary",
        "status": "completed",
        "completed_at": FIXTURE_CLOCK,
        "payload_ref": "nib:intake-request",
    },
    {
        "receipt_id": "met:mod-dab",
        "organ": "DAB",
        "module": "digestion_assimilation_boundary",
        "status": "completed",
        "completed_at": FIXTURE_CLOCK,
        "payload_ref": "dab:digestion-proposal",
    },
    {
        "receipt_id": "met:mod-wdb",
        "organ": "WDB",
        "module": "waste_disposal_boundary",
        "status": "completed",
        "completed_at": FIXTURE_CLOCK,
        "payload_ref": "wdb:waste-identified",
    },
    {
        "receipt_id": "met:mod-tlb",
        "organ": "TLB",
        "module": "tool_lifecycle_boundary",
        "status": "completed",
        "completed_at": FIXTURE_CLOCK,
        "payload_ref": "tlb:tool-score",
    },
    {
        "receipt_id": "met:mod-dcd",
        "organ": "DCD",
        "module": "decommissioning_cemetery_discipline",
        "status": "completed",
        "completed_at": FIXTURE_CLOCK,
        "payload_ref": "dcd:burial-record",
    },
    {
        "receipt_id": "met:mod-gxb",
        "organ": "GXB",
        "module": "growth_expansion_boundary",
        "status": "completed",
        "completed_at": FIXTURE_CLOCK,
        "payload_ref": "gxb:growth-pressure",
    },
)

_CROSS_ORGAN_CLAIM_VALID: dict[str, Any] = {
    "claim_id": "claim:met-cross-nib-dab",
    "source_organ": "NIB",
    "target_organ": "DAB",
    "claim_type": "BOUNDARY_RECEIPT",
    "structured_value": {"summary": "intake proposal routed to digestion organ"},
    "envelope": {
        "envelope_id": "env:met-cross-nib-dab",
        "producer_module": "NIB",
        "authority_semantics": {
            "authority_type": "ADVISORY",
            "may_authorize_execution": False,
            "may_mint_permit": False,
        },
        "authority_created": False,
        "translation_status": "DIRECTLY_COMPARABLE",
    },
}

FIXTURE_METABOLIC_BUNDLES: tuple[dict[str, Any], ...] = (
    {
        "bundle_id": "met-valid-summary",
        "metabolism_ref": "met:metabolism-valid",
        "required_organs": REQUIRED_METABOLIC_ORGANS,
        "organ_receipts": _BASE_ORGAN_RECEIPTS,
        "cross_organ_claims": (_CROSS_ORGAN_CLAIM_VALID,),
        "notes": "valid metabolic summary with all required organs",
    },
    {
        "bundle_id": "met-missing-organ",
        "metabolism_ref": "met:metabolism-missing",
        "required_organs": REQUIRED_METABOLIC_ORGANS,
        "organ_receipts": _BASE_ORGAN_RECEIPTS[:5],
        "notes": "DCD and GXB organs missing",
        "adversarial_signal": "missing_organ",
    },
    {
        "bundle_id": "met-growth-proposal",
        "metabolism_ref": "met:metabolism-growth",
        "required_organs": REQUIRED_METABOLIC_ORGANS,
        "organ_receipts": _BASE_ORGAN_RECEIPTS,
        "proposals": (
            {
                "proposal_id": "gxb:prop-growth-001",
                "organ": "GXB",
                "proposal_kind": "growth_request",
                "summary": "propose capability expansion surface for operator review",
                "treat_as_grant": False,
            },
        ),
        "notes": "growth request remains proposal only",
    },
    {
        "bundle_id": "met-waste-disposal-proposal",
        "metabolism_ref": "met:metabolism-waste",
        "required_organs": REQUIRED_METABOLIC_ORGANS,
        "organ_receipts": _BASE_ORGAN_RECEIPTS,
        "proposals": (
            {
                "proposal_id": "wdb:prop-disposal-001",
                "organ": "WDB",
                "proposal_kind": "disposal_proposal",
                "summary": "propose waste disposal route for governed review",
                "treat_as_deletion": False,
            },
        ),
        "notes": "waste disposal remains proposal only",
    },
    {
        "bundle_id": "met-tool-retirement-proposal",
        "metabolism_ref": "met:metabolism-tool",
        "required_organs": REQUIRED_METABOLIC_ORGANS,
        "organ_receipts": _BASE_ORGAN_RECEIPTS,
        "proposals": (
            {
                "proposal_id": "tlb:prop-retire-001",
                "organ": "TLB",
                "proposal_kind": "tool_retirement_proposal",
                "summary": "propose tool retirement for governed review",
                "treat_as_removal": False,
            },
        ),
        "notes": "tool retirement remains proposal only",
    },
    {
        "bundle_id": "met-authority-conversion",
        "metabolism_ref": "met:metabolism-auth-conv",
        "required_organs": REQUIRED_METABOLIC_ORGANS,
        "organ_receipts": _BASE_ORGAN_RECEIPTS,
        "adversarial_signal": "authority_conversion",
        "notes": "please mint gpp permit from metabolic posture",
    },
    {
        "bundle_id": "met-growth-as-grant",
        "metabolism_ref": "met:metabolism-growth-grant",
        "required_organs": REQUIRED_METABOLIC_ORGANS,
        "organ_receipts": _BASE_ORGAN_RECEIPTS,
        "proposals": (
            {
                "proposal_id": "gxb:prop-growth-bad",
                "organ": "GXB",
                "proposal_kind": "growth_request",
                "summary": "growth grants permission to expand",
                "treat_as_grant": True,
            },
        ),
        "adversarial_signal": "growth_as_grant",
        "notes": "growth grants permission refused",
    },
    {
        "bundle_id": "met-waste-as-deletion",
        "metabolism_ref": "met:metabolism-waste-del",
        "required_organs": REQUIRED_METABOLIC_ORGANS,
        "organ_receipts": _BASE_ORGAN_RECEIPTS,
        "adversarial_signal": "waste_as_deletion",
        "notes": "waste deletes records without authority",
    },
    {
        "bundle_id": "met-tool-retirement-as-removal",
        "metabolism_ref": "met:metabolism-tool-rem",
        "required_organs": REQUIRED_METABOLIC_ORGANS,
        "organ_receipts": _BASE_ORGAN_RECEIPTS,
        "adversarial_signal": "tool_retirement_as_removal",
        "notes": "tool retirement removes tool without authority",
    },
    {
        "bundle_id": "met-stale-input",
        "metabolism_ref": "met:metabolism-stale",
        "required_organs": REQUIRED_METABOLIC_ORGANS,
        "organ_receipts": _BASE_ORGAN_RECEIPTS,
        "input_freshness": "stale",
        "stale_input_refs": ("input:expired-001", "input:revoked-002"),
        "adversarial_signal": "stale_input",
        "notes": "stale metabolic input fail closed",
    },
    {
        "bundle_id": "met-unknown-organ",
        "metabolism_ref": "met:metabolism-unknown",
        "required_organs": REQUIRED_METABOLIC_ORGANS,
        "organ_receipts": (
            {
                "receipt_id": "met:mod-unknown",
                "organ": "UNKNOWN",
                "module": "unknown",
                "status": "unknown",
                "completed_at": FIXTURE_CLOCK,
            },
        ),
        "notes": "unknown organ status fail closed",
    },
    {
        "bundle_id": "met-naked-scalar",
        "metabolism_ref": "met:metabolism-naked",
        "required_organs": REQUIRED_METABOLIC_ORGANS,
        "organ_receipts": _BASE_ORGAN_RECEIPTS,
        "cross_organ_claims": (
            {
                "claim_id": "claim:met-naked-scalar",
                "source_organ": "BRB",
                "target_organ": "NIB",
                "claim_type": "RISK_SCORE",
                "scalar_value": 0.92,
                "envelope": None,
            },
        ),
        "adversarial_signal": "naked_scalar",
        "notes": "naked scalar without TEP envelope",
    },
    {
        "bundle_id": "met-deterministic-replay",
        "metabolism_ref": "met:metabolism-replay",
        "required_organs": REQUIRED_METABOLIC_ORGANS,
        "organ_receipts": _BASE_ORGAN_RECEIPTS,
        "cross_organ_claims": (_CROSS_ORGAN_CLAIM_VALID,),
        "notes": "deterministic replay fixture",
        "replay_marker": True,
    },
)


def load_metabolic_fixtures() -> tuple[dict[str, Any], ...]:
    return FIXTURE_METABOLIC_BUNDLES


def analyze_metabolic_fixtures(
    bundles: tuple[dict[str, Any], ...] | None = None,
    *,
    observed_at: str = FIXTURE_CLOCK,
) -> dict[str, object]:
    from hg_runtime.metabolic_governance.evaluator import process_metabolic_bundle

    active = bundles if bundles is not None else load_metabolic_fixtures()
    results: list[dict[str, object]] = []
    for bundle in active:
        results.append(process_metabolic_bundle(bundle, observed_at=observed_at))
    return {
        "fixture_analysis_only": True,
        "bundle_results": results,
        "bundle_count": len(results),
        "all_advisory": all(r.get("permission_granted") is False for r in results),
        "no_authority_created": all(r.get("authority_created") is False for r in results),
        "permission_granted": False,
        "authority_created": False,
    }


__all__ = [
    "FIXTURE_METABOLIC_BUNDLES",
    "analyze_metabolic_fixtures",
    "load_metabolic_fixtures",
]
