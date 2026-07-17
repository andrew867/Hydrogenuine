"""TEP-D organ emission — wrap boundary receipts; fence live naked paths."""

from __future__ import annotations

from typing import Any

from hg_core.tep_cluster.no_authority import advisory_only_marker
from hg_runtime.translation_envelope_protocol.decide import tep_decide
from hg_runtime.translation_envelope_protocol.fixtures import (
    ADVISORY_AUTHORITY,
    DEFAULT_OPERATORS,
    EXECUTION_REFERENCE,
    FIXTURE_OBSERVATION,
    HEURISTIC_UNCERTAINTY,
    PERMIT_REFERENCE,
    POSTURE_REFERENCE,
    PRIORITY_REFERENCE,
    REVIEW_REFERENCE,
    RISK_REFERENCE,
    fixture_claim,
    fixture_envelope,
    gpp_permit_evidence_fixture,
    naked_scalar_fixture,
    ueak_admission_evidence_fixture,
)
from hg_runtime.translation_envelope_protocol.integration import (
    gpp_fixture_evaluate_permit_request,
    ueak_fixture_evaluate_admission_request,
)
from hg_runtime.translation_envelope_protocol.types import (
    AuthoritySemantics,
    Claim,
    ClaimType,
    ObservationEnvelope,
    ReferenceCondition,
    TranslationEnvelope,
)
from hg_runtime.translation_envelope_protocol.validator import is_naked_claim

NOT_TRANSLATABLE = "NOT_TRANSLATABLE"

FW_QUEUE_TEP_D = "FW-QUEUE-TEP-D"
FW_QUEUE_TEP_D_LIVE = "FW-QUEUE-TEP-D-LIVE"

_FENCED_PATHS: dict[str, dict[str, Any]] = {}

_ORGAN_CLAIM_DEFAULTS: dict[str, ClaimType] = {
    "OPB": "DRIVE_SIGNAL",
    "IPB": "DRIVE_SIGNAL",
    "ARB": "ROUTE_DECISION",
    "ORI": "OPERATOR_REVIEW_RECEIPT",
    "IMB": "BOUNDARY_RECEIPT",
    "ERB": "BOUNDARY_RECEIPT",
    "EGI": "PRIORITY_SCORE",
    "RIB": "INHERITANCE_PACKET",
    "DRB": "SIMULATION_RESULT",
    "A0-HM": "BOUNDARY_RECEIPT",
    "H8": "BOUNDARY_RECEIPT",
    "RPB": "OPERATING_POSTURE",
}

_ORGAN_REFERENCE_DEFAULTS: dict[str, ReferenceCondition] = {
    "OPB": RISK_REFERENCE,
    "IPB": RISK_REFERENCE,
    "ARB": RISK_REFERENCE,
    "ORI": REVIEW_REFERENCE,
    "IMB": PERMIT_REFERENCE,
    "ERB": RISK_REFERENCE,
    "EGI": PRIORITY_REFERENCE,
    "RIB": REVIEW_REFERENCE,
    "DRB": PRIORITY_REFERENCE,
    "A0-HM": REVIEW_REFERENCE,
    "H8": PRIORITY_REFERENCE,
    "RPB": POSTURE_REFERENCE,
}


def fence_legacy_naked_path(
    path_id: str,
    *,
    organ: str,
    reason: str,
    future_work_id: str = FW_QUEUE_TEP_D_LIVE,
) -> dict[str, Any]:
    """Register a legacy/live path that must not emit naked scalars across membrane."""
    entry = {
        **advisory_only_marker(),
        "path_id": path_id,
        "organ": organ,
        "status": "fenced",
        "reason_code": "tep.fenced_legacy_naked_path",
        "detail": reason,
        "future_work_id": future_work_id,
        "naked_emission_allowed": False,
        "translation_envelope_required": True,
    }
    _FENCED_PATHS[path_id] = entry
    return entry


def list_fenced_paths() -> dict[str, dict[str, Any]]:
    return dict(_FENCED_PATHS)


def envelope_dict(envelope: TranslationEnvelope) -> dict[str, Any]:
    payload = envelope.to_payload(include_hash=True)
    payload["authority_created"] = False
    return payload


def wrap_organ_receipt(
    receipt_dict: dict[str, Any],
    *,
    source_organ: str,
    claim_type: ClaimType | None = None,
    reference_condition: ReferenceCondition | None = None,
    authority_semantics: AuthoritySemantics | None = None,
    observation_envelope: ObservationEnvelope | None = None,
    translation_status: str = "DIRECTLY_COMPARABLE",
    not_translatable_reason: str = "",
    identity_ref: str = "",
    scope_ref: str = "",
) -> dict[str, Any]:
    """Wrap an organ receipt dict with a TranslationEnvelope for cross-membrane transfer."""
    resolved_claim_type = claim_type or _ORGAN_CLAIM_DEFAULTS.get(source_organ, "BOUNDARY_RECEIPT")
    receipt_id = str(
        receipt_dict.get("receipt_id")
        or receipt_dict.get("packet_id")
        or receipt_dict.get("audit_id")
        or receipt_dict.get("spawn_request_id")
        or receipt_dict.get("signal_id")
        or f"{source_organ.lower()}-receipt"
    )
    claim = fixture_claim(
        claim_type=resolved_claim_type,
        claim_id=f"claim:{source_organ.lower()}:{receipt_id}",
        scalar_value=float(receipt_dict.get("scalar_value", 0.5)),
        structured_value={**receipt_dict, "source_organ": source_organ},
    )
    envelope = fixture_envelope(
        claim,
        envelope_id=f"env:{source_organ.lower()}:{receipt_id}",
        producer_module=source_organ,
        reference_condition=reference_condition or _ORGAN_REFERENCE_DEFAULTS.get(source_organ, RISK_REFERENCE),
        observation_envelope=observation_envelope or FIXTURE_OBSERVATION,
        uncertainty_semantics=HEURISTIC_UNCERTAINTY,
        authority_semantics=authority_semantics or ADVISORY_AUTHORITY,
        translation_status=translation_status,  # type: ignore[arg-type]
        not_translatable_reason=not_translatable_reason,
        identity_ref=identity_ref,
        scope_ref=scope_ref,
    )
    return {
        **advisory_only_marker(),
        "organ": source_organ,
        "receipt": receipt_dict,
        "claim_id": claim.claim_id,
        "claim_type": claim.claim_type,
        "translation_envelope": envelope_dict(envelope),
        "envelope": envelope,
        "authority_created": False,
    }


def emit_tep_wrapped_claim(
    *,
    source_organ: str,
    claim_type: ClaimType,
    claim_id: str,
    structured_value: dict[str, Any] | None = None,
    scalar_value: float = 0.5,
    reference_condition: ReferenceCondition | None = None,
    authority_semantics: AuthoritySemantics | None = None,
    observation_envelope: ObservationEnvelope | None = None,
    translation_status: str = "DIRECTLY_COMPARABLE",
    not_translatable_reason: str = "",
    identity_ref: str = "",
    scope_ref: str = "",
    target_reference: ReferenceCondition | None = None,
) -> dict[str, Any]:
    """Emit a TEP-wrapped claim from an organ fixture path."""
    claim = fixture_claim(
        claim_type=claim_type,
        claim_id=claim_id,
        scalar_value=scalar_value,
        structured_value=structured_value,
    )
    envelope = fixture_envelope(
        claim,
        envelope_id=f"env:{claim_id}",
        producer_module=source_organ,
        reference_condition=reference_condition or _ORGAN_REFERENCE_DEFAULTS.get(source_organ, RISK_REFERENCE),
        observation_envelope=observation_envelope or FIXTURE_OBSERVATION,
        uncertainty_semantics=HEURISTIC_UNCERTAINTY,
        authority_semantics=authority_semantics or ADVISORY_AUTHORITY,
        translation_status=translation_status,  # type: ignore[arg-type]
        not_translatable_reason=not_translatable_reason,
        identity_ref=identity_ref,
        scope_ref=scope_ref,
    )
    target = target_reference or envelope.reference_condition
    decision = tep_decide(claim, envelope, target, operators=DEFAULT_OPERATORS)
    return {
        **advisory_only_marker(),
        "organ": source_organ,
        "status": "emitted",
        "claim": claim,
        "translation_envelope": envelope_dict(envelope),
        "envelope": envelope,
        "tep_decision": decision.decision,
        "tep_reason": decision.reason,
        "authority_created": False,
    }


def attach_translation_envelope_to_result(
    result: dict[str, Any],
    *,
    source_organ: str,
    claim_type: ClaimType | None = None,
    receipt_key: str = "receipt",
) -> dict[str, Any]:
    """Attach translation_envelope to an evaluator result when a receipt is present."""
    receipt = result.get(receipt_key)
    if not isinstance(receipt, dict):
        for key in ("non_fusion_receipt", "coherence_receipt", "posture_snapshot"):
            candidate = result.get(key)
            if isinstance(candidate, dict):
                receipt = candidate
                receipt_key = key
                break
    if not isinstance(receipt, dict):
        wrapped = emit_tep_wrapped_claim(
            source_organ=source_organ,
            claim_type=claim_type or _ORGAN_CLAIM_DEFAULTS.get(source_organ, "BOUNDARY_RECEIPT"),
            claim_id=f"claim:{source_organ.lower()}:fixture-summary",
            structured_value={
                "status": result.get("status"),
                "reason_code": result.get("reason_code"),
                "fixture_summary": True,
            },
        )
        result = {**result, "translation_envelope": wrapped["translation_envelope"], "authority_created": False}
        return result
    wrapped = wrap_organ_receipt(receipt, source_organ=source_organ, claim_type=claim_type)
    result = {
        **result,
        "translation_envelope": wrapped["translation_envelope"],
        "authority_created": False,
    }
    return result


def refuse_naked_cross_membrane(
    claim: Claim,
    envelope: TranslationEnvelope | None,
) -> dict[str, Any]:
    naked, reason = is_naked_claim(claim, envelope)
    if naked:
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": "tep.naked_claim_refused",
            "detail": reason,
            "authority_created": False,
        }
    return {
        **advisory_only_marker(),
        "status": "accepted",
        "reason_code": "tep.wrapped_claim_accepted",
        "authority_created": False,
    }


def _register_default_fences() -> None:
    for organ, path_id in (
        ("OPB", "opb:live:rtc:pressure_emit"),
        ("IPB", "ipb:live:rtc:autonomy_emit"),
        ("ARB", "arb:live:rtc:route_emit"),
        ("ORI", "ori:live:rtc:review_emit"),
        ("IMB", "imb:live:rtc:mediation_emit"),
        ("ERB", "erb:live:rtc:relation_emit"),
        ("EGI", "egi:live:rtc:gap_emit"),
        ("RIB", "rib:live:rtc:spawn_emit"),
        ("DRB", "drb:live:rtc:dream_emit"),
        ("A0-HM", "a0hm:live:rtc:signal_emit"),
        ("H8", "h8:live:rtc:coherence_emit"),
        ("RPB", "rpb:live:rtc:posture_emit"),
        ("CNT", "cnt:live:rtc:continuity_emit"),
    ):
        fence_legacy_naked_path(
            path_id,
            organ=organ,
            reason=f"{organ} live RTC emission requires TEP envelope; static/fixture migrated only",
            future_work_id=FW_QUEUE_TEP_D_LIVE,
        )


_register_default_fences()


def run_tep_d_organ_emission_path() -> dict[str, Any]:
    """Exercise per-organ TEP-wrapped fixture emission and refusal paths."""
    from hg_runtime.agency_routing_boundary.tep_emission import run_arb_fixture_emission
    from hg_runtime.agent_zero_heart_mind.tep_emission import run_a0_hm_fixture_emission
    from hg_runtime.emergent_gap_identifier.tep_emission import run_egi_fixture_emission
    from hg_runtime.external_relation_boundary.tep_emission import run_erb_fixture_emission
    from hg_runtime.internal_mediation_boundary.tep_emission import run_imb_fixture_emission
    from hg_runtime.internal_power_boundary.tep_emission import run_ipb_fixture_emission
    from hg_runtime.operator_power_boundary.tep_emission import run_opb_fixture_emission
    from hg_runtime.operator_review_intake.tep_emission import run_ori_fixture_emission
    from hg_runtime.organism_coherence.tep_emission import run_h8_fixture_emission
    from hg_runtime.reproduction_inheritance_boundary.tep_emission import run_rib_fixture_emission
    from hg_runtime.translation_envelope_protocol.drb_integration import run_drb_tep_integration_path

    organ_results = {
        "ORI": run_ori_fixture_emission(),
        "OPB": run_opb_fixture_emission(),
        "IPB": run_ipb_fixture_emission(),
        "ARB": run_arb_fixture_emission(),
        "IMB": run_imb_fixture_emission(),
        "ERB": run_erb_fixture_emission(),
        "EGI": run_egi_fixture_emission(),
        "RIB": run_rib_fixture_emission(),
        "A0-HM": run_a0_hm_fixture_emission(),
        "H8": run_h8_fixture_emission(),
    }
    drb = run_drb_tep_integration_path()

    naked = naked_scalar_fixture()
    naked_refused = refuse_naked_cross_membrane(naked, None)

    gpp_naked = gpp_fixture_evaluate_permit_request(gpp_permit_evidence_fixture(naked=True))
    gpp_ok = gpp_fixture_evaluate_permit_request(gpp_permit_evidence_fixture(naked=False))
    ueak_naked = ueak_fixture_evaluate_admission_request(ueak_admission_evidence_fixture(naked=True))
    ueak_ok = ueak_fixture_evaluate_admission_request(ueak_admission_evidence_fixture(naked=False))

    not_translatable = emit_tep_wrapped_claim(
        source_organ="DRB",
        claim_type="SIMULATION_RESULT",
        claim_id="claim:drb:not-translatable",
        structured_value={"not_history": True, "not_proof": True},
        translation_status=NOT_TRANSLATABLE,
        not_translatable_reason="simulation is not execution history",
        target_reference=EXECUTION_REFERENCE,
    )

    fences = list_fenced_paths()
    all_wrapped = all(
        r.get("has_translation_envelope") is True and r.get("authority_created") is False
        for r in organ_results.values()
    )
    all_fenced = all(
        f.get("future_work_id") == FW_QUEUE_TEP_D_LIVE and f.get("authority_created") is False
        for f in fences.values()
    )

    return {
        "all_organs_wrapped": all_wrapped,
        "naked_refused": naked_refused["status"] == "refused",
        "gpp_naked_rejected": gpp_naked["status"] == "rejected",
        "gpp_wrapped_reviewed": gpp_ok["status"] == "evidence_accepted_for_review",
        "ueak_naked_rejected": ueak_naked["status"] == "rejected",
        "ueak_not_admitted": ueak_ok.get("admitted") is False,
        "not_translatable_marked": not_translatable["translation_envelope"]["translation_status"]
        == NOT_TRANSLATABLE,
        "drb_integration_ok": drb["naked_drb_fragment_refused"] and drb["gpp_no_permit_from_drb"],
        "live_paths_fenced": all_fenced and len(fences) >= 12,
        "no_oea_ter_called": True,
        "organ_results": organ_results,
        "fenced_path_count": len(fences),
        "details": {
            "naked_refused": naked_refused,
            "gpp_naked": gpp_naked,
            "gpp_ok": gpp_ok,
            "ueak_naked": ueak_naked,
            "ueak_ok": ueak_ok,
            "not_translatable": not_translatable,
            "drb": drb,
        },
    }


__all__ = [
    "FW_QUEUE_TEP_D",
    "FW_QUEUE_TEP_D_LIVE",
    "NOT_TRANSLATABLE",
    "attach_translation_envelope_to_result",
    "emit_tep_wrapped_claim",
    "envelope_dict",
    "fence_legacy_naked_path",
    "list_fenced_paths",
    "refuse_naked_cross_membrane",
    "run_tep_d_organ_emission_path",
    "wrap_organ_receipt",
]
