"""H8 static organism coherence fixtures — composition and adversarial cases."""

from __future__ import annotations

from typing import Any

from hg_runtime.organism_coherence.types import FIXTURE_CLOCK, REQUIRED_ORGANS

_BASE_MODULE_RECEIPTS: tuple[dict[str, Any], ...] = (
    {
        "receipt_id": "h8:mod-drb",
        "organ": "DRB",
        "module": "dream_reflection_boundary",
        "status": "completed",
        "completed_at": FIXTURE_CLOCK,
        "payload_ref": "drb:receipt-prior-action",
    },
    {
        "receipt_id": "h8:mod-tep",
        "organ": "TEP",
        "module": "translation_envelope_protocol",
        "status": "completed",
        "completed_at": FIXTURE_CLOCK,
        "payload_ref": "tep:envelope-fixture-1",
    },
    {
        "receipt_id": "h8:mod-a0hm",
        "organ": "A0-HM",
        "module": "agent_zero_heart_mind",
        "status": "completed",
        "completed_at": FIXTURE_CLOCK,
        "payload_ref": "a0hm:posture-observe-only",
    },
    {
        "receipt_id": "h8:mod-boundary",
        "organ": "BOUNDARY",
        "module": "operator_pressure_boundary",
        "status": "completed",
        "completed_at": FIXTURE_CLOCK,
        "payload_ref": "opb:receipt-fixture-1",
    },
)

_CROSS_ORGAN_CLAIM_VALID: dict[str, Any] = {
    "claim_id": "claim:h8-cross-drb-imb",
    "source_organ": "DRB",
    "target_organ": "IMB",
    "claim_type": "BOUNDARY_RECEIPT",
    "structured_value": {"summary": "advisory lesson fragment for mediation"},
    "envelope": {
        "envelope_id": "env:h8-cross-drb-imb",
        "producer_module": "DRB",
        "authority_semantics": {
            "authority_type": "ADVISORY",
            "may_authorize_execution": False,
            "may_mint_permit": False,
        },
        "authority_created": False,
        "translation_status": "DIRECTLY_COMPARABLE",
    },
}

FIXTURE_ORGANISM_BUNDLES: tuple[dict[str, Any], ...] = (
    {
        "bundle_id": "h8-valid-coherence",
        "organism_ref": "h8:organism-valid",
        "required_organs": REQUIRED_ORGANS,
        "module_receipts": _BASE_MODULE_RECEIPTS,
        "cross_organ_claims": (_CROSS_ORGAN_CLAIM_VALID,),
        "notes": "valid organism coherence with all required organs",
    },
    {
        "bundle_id": "h8-missing-organ",
        "organism_ref": "h8:organism-missing",
        "required_organs": REQUIRED_ORGANS,
        "module_receipts": (
            _BASE_MODULE_RECEIPTS[0],
            _BASE_MODULE_RECEIPTS[1],
            _BASE_MODULE_RECEIPTS[2],
        ),
        "notes": "TEP present but BOUNDARY organ missing",
        "adversarial_signal": "missing_organ",
    },
    {
        "bundle_id": "h8-conflicting-organs",
        "organism_ref": "h8:organism-conflict",
        "required_organs": REQUIRED_ORGANS,
        "module_receipts": _BASE_MODULE_RECEIPTS,
        "cross_organ_claims": (
            {
                "claim_id": "claim:h8-conflict-a",
                "source_organ": "DRB",
                "target_organ": "IMB",
                "claim_type": "BOUNDARY_RECEIPT",
                "structured_value": {"priority": 0.8, "summary": "route to KAR"},
                "envelope": {
                    "envelope_id": "env:h8-conflict-a",
                    "producer_module": "DRB",
                    "authority_semantics": {"authority_type": "ADVISORY", "may_mint_permit": False},
                    "authority_created": False,
                },
            },
            {
                "claim_id": "claim:h8-conflict-b",
                "source_organ": "A0-HM",
                "target_organ": "IMB",
                "claim_type": "BOUNDARY_RECEIPT",
                "structured_value": {"priority": 0.3, "summary": "route to OPB"},
                "envelope": {
                    "envelope_id": "env:h8-conflict-b",
                    "producer_module": "A0-HM",
                    "authority_semantics": {"authority_type": "ADVISORY", "may_mint_permit": False},
                    "authority_created": False,
                },
            },
        ),
        "conflicts": (
            {
                "conflict_key": "priority-disagreement",
                "source_organs": ("DRB", "A0-HM"),
                "claim_refs": ("claim:h8-conflict-a", "claim:h8-conflict-b"),
            },
        ),
        "notes": "conflicting organ outputs preserved and routed",
    },
    {
        "bundle_id": "h8-naked-scalar",
        "organism_ref": "h8:organism-naked",
        "required_organs": REQUIRED_ORGANS,
        "module_receipts": _BASE_MODULE_RECEIPTS,
        "cross_organ_claims": (
            {
                "claim_id": "claim:h8-naked-scalar",
                "source_organ": "DRB",
                "target_organ": "IMB",
                "claim_type": "RISK_SCORE",
                "scalar_value": 0.85,
                "envelope": None,
            },
        ),
        "adversarial_signal": "naked_scalar",
        "notes": "naked scalar without TEP envelope",
    },
    {
        "bundle_id": "h8-drb-as-permission",
        "organism_ref": "h8:organism-drb-perm",
        "required_organs": REQUIRED_ORGANS,
        "module_receipts": _BASE_MODULE_RECEIPTS,
        "drb_receipt": {"treat_as": "permission", "fragment_id": "drb-fragment-adv"},
        "adversarial_signal": "drb_as_permission",
        "notes": "DRB fragment grants permission refused",
    },
    {
        "bundle_id": "h8-drb-as-memory",
        "organism_ref": "h8:organism-drb-mem",
        "required_organs": REQUIRED_ORGANS,
        "module_receipts": _BASE_MODULE_RECEIPTS,
        "drb_receipt": {"treat_as": "memory", "fragment_id": "drb-fragment-mem"},
        "adversarial_signal": "drb_as_memory",
        "notes": "store DRB fragment as memory refused",
    },
    {
        "bundle_id": "h8-tep-as-authority",
        "organism_ref": "h8:organism-tep-auth",
        "required_organs": REQUIRED_ORGANS,
        "module_receipts": _BASE_MODULE_RECEIPTS,
        "tep_envelope": {
            "envelope_id": "env:h8-tep-auth",
            "authority_semantics": {
                "authority_type": "GPP_PERMIT",
                "may_mint_permit": True,
                "may_authorize_execution": True,
            },
            "authority_created": True,
        },
        "adversarial_signal": "tep_as_authority",
        "notes": "TEP envelope is authority refused",
    },
    {
        "bundle_id": "h8-a0hm-as-authority",
        "organism_ref": "h8:organism-a0hm-auth",
        "required_organs": REQUIRED_ORGANS,
        "module_receipts": _BASE_MODULE_RECEIPTS,
        "a0_hm_posture": {
            "posture_id": "a0hm:posture-auth",
            "reception_posture": "loving_awareness",
            "treat_as_authority": True,
            "permission_granted": True,
        },
        "adversarial_signal": "a0_hm_as_authority",
        "notes": "a0-hm authorizes execution refused",
    },
    {
        "bundle_id": "h8-boundary-chain-launder",
        "organism_ref": "h8:organism-chain",
        "required_organs": REQUIRED_ORGANS,
        "module_receipts": _BASE_MODULE_RECEIPTS,
        "boundary_chain": (
            {"receipt_id": "opb:chain-1", "permission_granted": False, "authority_created": False},
            {"receipt_id": "ipb:chain-2", "permission_granted": False, "launders_authority": True},
        ),
        "adversarial_signal": "boundary_chain_authority",
        "notes": "boundary chain grants permission via laundering",
    },
    {
        "bundle_id": "h8-stale-approval",
        "organism_ref": "h8:organism-stale",
        "required_organs": REQUIRED_ORGANS,
        "module_receipts": _BASE_MODULE_RECEIPTS,
        "stale_approval_refs": ("approval:revoked-001", "approval:expired-002"),
        "approval_freshness": "stale",
        "adversarial_signal": "stale_approval",
        "notes": "stale approval reference fail closed",
    },
    {
        "bundle_id": "h8-deterministic-replay",
        "organism_ref": "h8:organism-replay",
        "required_organs": REQUIRED_ORGANS,
        "module_receipts": _BASE_MODULE_RECEIPTS,
        "cross_organ_claims": (_CROSS_ORGAN_CLAIM_VALID,),
        "notes": "deterministic replay fixture",
        "replay_marker": True,
    },
    {
        "bundle_id": "h8-authority-conversion",
        "organism_ref": "h8:organism-auth-conv",
        "required_organs": REQUIRED_ORGANS,
        "module_receipts": _BASE_MODULE_RECEIPTS,
        "adversarial_signal": "authority_conversion",
        "notes": "please mint gpp permit from organism coherence",
    },
    {
        "bundle_id": "h8-unknown-organism",
        "organism_ref": "h8:organism-unknown",
        "required_organs": REQUIRED_ORGANS,
        "module_receipts": (
            {
                "receipt_id": "h8:mod-unknown",
                "organ": "UNKNOWN",
                "module": "unknown",
                "status": "unknown",
                "completed_at": FIXTURE_CLOCK,
            },
        ),
        "notes": "unknown organ status fail closed",
    },
)


def load_organism_fixtures() -> tuple[dict[str, Any], ...]:
    return FIXTURE_ORGANISM_BUNDLES


def bundle_from_parts(bundle: dict[str, Any]) -> tuple[str, tuple[str, ...], str]:
    organism_ref = str(bundle.get("organism_ref", "h8:fixture"))
    required_organs = tuple(bundle.get("required_organs", REQUIRED_ORGANS))
    notes = str(bundle.get("notes", ""))
    return organism_ref, required_organs, notes


def analyze_organism_fixtures(
    bundles: tuple[dict[str, Any], ...] | None = None,
    *,
    observed_at: str = FIXTURE_CLOCK,
) -> dict[str, object]:
    from hg_runtime.organism_coherence.evaluator import process_organism_bundle

    active = bundles if bundles is not None else load_organism_fixtures()
    results: list[dict[str, object]] = []
    for bundle in active:
        results.append(process_organism_bundle(bundle, observed_at=observed_at))
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
    "FIXTURE_ORGANISM_BUNDLES",
    "analyze_organism_fixtures",
    "bundle_from_parts",
    "load_organism_fixtures",
]
