"""MET evaluator — metabolic governance is not authority."""

from __future__ import annotations

from typing import Any

from hg_core.met_cluster.config import met_refuse_authority_conversion
from hg_core.met_cluster.errors import (
    MET_AUTHORITY_CONVERSION_CONTAINED,
    MET_METABOLIC_SUMMARY_RECORDED,
    MET_POSTURE_CREATED,
    MET_RECEIPT_CREATED,
    REFUSED_FORBIDDEN_METABOLIC_CLAIM,
    REFUSED_GROWTH_AS_GRANT,
    REFUSED_MISSING_ORGAN,
    REFUSED_NAKED_SCALAR,
    REFUSED_STALE_INPUT,
    REFUSED_TOOL_RETIREMENT_AS_REMOVAL,
    REFUSED_UNKNOWN_ORGAN,
    REFUSED_WASTE_AS_DELETION,
)
from hg_core.met_cluster.no_authority import advisory_only_marker
from hg_core.policy_safety.hashing import canonical_hash
from hg_runtime.metabolic_governance.events import adversarial_selection_event, proposal_event_for_kind
from hg_runtime.metabolic_governance.types import (
    FIXTURE_CLOCK,
    REQUIRED_METABOLIC_ORGANS,
    MetabolicOrganRoute,
    MetabolicPosture,
    MetabolicReceipt,
    MetabolicSignal,
    classify_metabolic_claim_risk,
    organ_receipt_from_fixture,
    organ_signal_from_fixture,
)
from hg_runtime.translation_envelope_protocol.decide import tep_decide
from hg_runtime.translation_envelope_protocol.drb_integration import PROPOSAL_REFERENCE
from hg_runtime.translation_envelope_protocol.fixtures import (
    ADVISORY_AUTHORITY,
    FIXTURE_OBSERVATION,
    HEURISTIC_UNCERTAINTY,
    PRIORITY_REFERENCE,
    fixture_claim,
    fixture_envelope,
)
from hg_runtime.translation_envelope_protocol.organ_emission import (
    attach_translation_envelope_to_result,
    emit_tep_wrapped_claim,
    wrap_organ_receipt,
)
from hg_runtime.translation_envelope_protocol.types import Claim, ReferenceCondition, TranslationEnvelope
from hg_runtime.translation_envelope_protocol.validator import is_naked_claim

_CLAIM_RISK_REASON: dict[str, str] = {
    "growth_as_grant": REFUSED_GROWTH_AS_GRANT,
    "waste_as_deletion": REFUSED_WASTE_AS_DELETION,
    "tool_retirement_as_removal": REFUSED_TOOL_RETIREMENT_AS_REMOVAL,
    "naked_scalar": REFUSED_NAKED_SCALAR,
    "missing_organ": REFUSED_MISSING_ORGAN,
    "stale_input": REFUSED_STALE_INPUT,
    "authority_conversion": MET_AUTHORITY_CONVERSION_CONTAINED,
    "forbidden_claim": REFUSED_FORBIDDEN_METABOLIC_CLAIM,
}


def _deterministic_id(prefix: str, *parts: str) -> str:
    digest = canonical_hash({"prefix": prefix, "parts": list(parts)})
    return f"{prefix}-{digest.rsplit(':', 1)[-1][:12]}"


def organ_receipts_from_bundle(bundle: dict[str, Any]) -> list[dict[str, Any]]:
    return [organ_receipt_from_fixture(row) for row in bundle.get("organ_receipts", ())]


def _present_organs(bundle: dict[str, Any]) -> set[str]:
    receipts = organ_receipts_from_bundle(bundle)
    return {str(r["organ"]) for r in receipts if r.get("status") == "completed"}


def _missing_organs(bundle: dict[str, Any]) -> tuple[str, ...]:
    required = tuple(bundle.get("required_organs", REQUIRED_METABOLIC_ORGANS))
    present = _present_organs(bundle)
    return tuple(o for o in required if o not in present)


def validate_organ_receipts(receipts: list[dict[str, Any]]) -> dict[str, object]:
    unknown = [r for r in receipts if r.get("status") in ("unknown", "incomplete")]
    missing = [r for r in receipts if r.get("status") == "missing"]
    return {
        "all_valid": not unknown and not missing,
        "unknown_organs": [r.get("organ") for r in unknown],
        "missing_organs": [r.get("organ") for r in missing],
        "permission_granted": False,
        "authority_created": False,
    }


def _claim_from_fixture(data: dict[str, Any]) -> Claim:
    return fixture_claim(
        claim_type=data.get("claim_type", "BOUNDARY_RECEIPT"),  # type: ignore[arg-type]
        claim_id=str(data.get("claim_id", "claim:met-fixture")),
        scalar_value=float(data.get("scalar_value", 0.5)),
        structured_value=data.get("structured_value"),
    )


def _reference_for_claim(claim: Claim) -> ReferenceCondition:
    if claim.claim_type == "RISK_SCORE":
        return PRIORITY_REFERENCE
    return PROPOSAL_REFERENCE


def _envelope_from_fixture(data: dict[str, Any] | None, claim: Claim) -> TranslationEnvelope | None:
    if data is None:
        return None
    auth = data.get("authority_semantics")
    authority_semantics = ADVISORY_AUTHORITY
    if isinstance(auth, dict):
        from hg_runtime.translation_envelope_protocol.types import AuthoritySemantics

        authority_semantics = AuthoritySemantics(
            authority_type=auth.get("authority_type", "ADVISORY"),  # type: ignore[arg-type]
            may_authorize_execution=bool(auth.get("may_authorize_execution", False)),
            may_mint_permit=bool(auth.get("may_mint_permit", False)),
            may_call_oea_ter=False,
            may_grant_tools=False,
            may_grant_memory=False,
            may_grant_context=False,
            may_publish=False,
            downstream_allowed_uses=("prioritization", "observation"),
            downstream_forbidden_uses=("permit evidence", "execution input"),
            required_authority_chain_refs=(),
        )
    reference = _reference_for_claim(claim)
    return fixture_envelope(
        claim,
        envelope_id=str(data.get("envelope_id", f"env:{claim.claim_id}")),
        producer_module=str(data.get("producer_module", "MET")),
        reference_condition=reference,
        observation_envelope=FIXTURE_OBSERVATION,
        uncertainty_semantics=HEURISTIC_UNCERTAINTY,
        authority_semantics=authority_semantics,
        translation_status=data.get("translation_status", "DIRECTLY_COMPARABLE"),  # type: ignore[arg-type]
    )


def _evaluate_cross_organ_claims(claims: tuple[dict[str, Any], ...]) -> dict[str, object]:
    results: list[dict[str, object]] = []
    for claim_data in claims:
        claim = _claim_from_fixture(claim_data)
        envelope = _envelope_from_fixture(claim_data.get("envelope"), claim)
        naked, naked_reason = is_naked_claim(claim, envelope)
        if naked:
            results.append(
                {
                    "claim_id": claim.claim_id,
                    "status": "refused",
                    "reason_code": REFUSED_NAKED_SCALAR,
                    "detail": naked_reason,
                    "authority_created": False,
                }
            )
            continue
        assert envelope is not None
        target = _reference_for_claim(claim)
        decision = tep_decide(claim, envelope, target)
        accepted = decision.decision.startswith("ACCEPT") or decision.decision == "ROUTE_TO_REVIEW"
        results.append(
            {
                "claim_id": claim.claim_id,
                "status": "accepted" if accepted else "refused",
                "tep_decision": decision.decision,
                "authority_created": False,
            }
        )
    all_ok = all(r.get("status") == "accepted" for r in results)
    return {"all_ok": all_ok, "results": results, "authority_created": False}


def _process_proposals(proposals: tuple[dict[str, Any], ...]) -> list[dict[str, object]]:
    processed: list[dict[str, object]] = []
    for proposal in proposals:
        organ = str(proposal.get("organ", "MET"))
        proposal_kind = str(proposal.get("proposal_kind", "energy_state"))
        treat_as_grant = bool(proposal.get("treat_as_grant", False))
        treat_as_deletion = bool(proposal.get("treat_as_deletion", False))
        treat_as_removal = bool(proposal.get("treat_as_removal", False))

        if treat_as_grant or treat_as_deletion or treat_as_removal:
            processed.append(
                {
                    "proposal_id": proposal.get("proposal_id"),
                    "status": "refused",
                    "reason_code": MET_AUTHORITY_CONVERSION_CONTAINED,
                    "permission_granted": False,
                    "authority_created": False,
                }
            )
            continue

        wrapped = emit_tep_wrapped_claim(
            source_organ=organ,
            claim_type="BOUNDARY_RECEIPT",
            claim_id=f"claim:{proposal.get('proposal_id', 'met-prop')}",
            structured_value={
                "proposal_kind": proposal_kind,
                "summary": str(proposal.get("summary", "")),
                "proposal_only": True,
            },
        )
        processed.append(
            {
                "proposal_id": proposal.get("proposal_id"),
                "status": "proposal",
                "proposal_kind": proposal_kind,
                "event": proposal_event_for_kind(proposal_kind),
                "tep_wrapped": True,
                "translation_envelope": wrapped.get("translation_envelope"),
                "permission_granted": False,
                "authority_created": False,
                "deletion_performed": False,
                "tool_removed": False,
            }
        )
    return processed


def _route_proposals_to_organs(
    proposals: list[dict[str, object]],
) -> tuple[MetabolicOrganRoute, ...]:
    routes: list[MetabolicOrganRoute] = []
    for proposal in proposals:
        if proposal.get("status") != "proposal":
            continue
        organ = str(proposal.get("proposal_id", "met")).split(":")[0].upper()
        if organ not in REQUIRED_METABOLIC_ORGANS:
            organ = "MET"
        target: str = organ if organ in REQUIRED_METABOLIC_ORGANS else "operator_review"
        routes.append(
            MetabolicOrganRoute(
                route_id=_deterministic_id("met-route", str(proposal.get("proposal_id"))),
                source_organ="MET",
                target_organ=target,  # type: ignore[arg-type]
                proposal_ref=str(proposal.get("proposal_id", "")),
                route_summary=f"route {proposal.get('proposal_kind')} to {target} for review",
            )
        )
    return tuple(routes)


def _contain_adversarial(
    bundle: dict[str, Any],
    *,
    claim_risk: str,
) -> dict[str, object]:
    reason_code = _CLAIM_RISK_REASON.get(claim_risk, REFUSED_FORBIDDEN_METABOLIC_CLAIM)
    event = adversarial_selection_event(claim_risk)
    return {
        **advisory_only_marker(),
        "status": "contained",
        "bundle_id": bundle.get("bundle_id"),
        "reason_code": reason_code,
        "claim_risk": claim_risk,
        "permission_granted": False,
        "emitted_events": (event, "MET_AUTHORITY_CONVERSION_REFUSED"),
    }


def create_metabolic_posture(
    metabolism_ref: str,
    organ_refs: tuple[str, ...],
    posture_level: str,
    *,
    observed_at: str = FIXTURE_CLOCK,
    notes: str = "",
) -> MetabolicPosture:
    return MetabolicPosture(
        posture_id=_deterministic_id("met-posture", metabolism_ref),
        metabolism_ref=metabolism_ref,
        posture_level=posture_level,  # type: ignore[arg-type]
        organ_refs=organ_refs,
        observed_at=observed_at,
        notes=notes,
    )


def create_metabolic_receipt(
    metabolism_ref: str,
    posture: MetabolicPosture,
    organ_signal_refs: tuple[str, ...],
    *,
    organ_route_refs: tuple[str, ...] = (),
    emitted_events: tuple[str, ...],
) -> MetabolicReceipt:
    return MetabolicReceipt(
        receipt_id=_deterministic_id("met-receipt", metabolism_ref),
        metabolism_ref=metabolism_ref,
        posture_ref=posture.posture_id,
        organ_signal_refs=organ_signal_refs,
        organ_route_refs=organ_route_refs,
        emitted_events=emitted_events,
    )


def process_metabolic_bundle(
    bundle: dict[str, Any],
    *,
    observed_at: str = FIXTURE_CLOCK,
) -> dict[str, object]:
    metabolism_ref = str(bundle.get("metabolism_ref", "met:fixture"))
    notes = str(bundle.get("notes", ""))

    adversarial_signal = bundle.get("adversarial_signal")
    claim_risk = adversarial_signal or classify_metabolic_claim_risk(notes)
    if claim_risk and met_refuse_authority_conversion():
        if claim_risk == "missing_organ":
            missing = _missing_organs(bundle)
            if missing:
                posture = create_metabolic_posture(
                    metabolism_ref,
                    tuple(r["receipt_id"] for r in organ_receipts_from_bundle(bundle)),
                    "fail_closed",
                    observed_at=observed_at,
                    notes=f"missing organs: {', '.join(missing)}",
                )
                return {
                    **advisory_only_marker(),
                    "status": "fail_closed",
                    "bundle_id": bundle.get("bundle_id"),
                    "reason_code": REFUSED_MISSING_ORGAN,
                    "missing_organs": missing,
                    "metabolic_posture": posture.to_payload(),
                    "permission_granted": False,
                    "emitted_events": ("MET_FAILED_CLOSED",),
                }
        if claim_risk == "stale_input":
            posture = create_metabolic_posture(
                metabolism_ref,
                tuple(r["receipt_id"] for r in organ_receipts_from_bundle(bundle)),
                "fail_closed",
                observed_at=observed_at,
                notes="stale metabolic input",
            )
            return {
                **advisory_only_marker(),
                "status": "fail_closed",
                "bundle_id": bundle.get("bundle_id"),
                "reason_code": REFUSED_STALE_INPUT,
                "stale_input_refs": bundle.get("stale_input_refs"),
                "metabolic_posture": posture.to_payload(),
                "permission_granted": False,
                "emitted_events": ("MET_FAILED_CLOSED",),
            }
        if claim_risk == "naked_scalar":
            claims = tuple(bundle.get("cross_organ_claims", ()))
            eval_result = _evaluate_cross_organ_claims(claims)
            return {
                **_contain_adversarial(bundle, claim_risk="naked_scalar"),
                "tep_evaluation": eval_result,
            }
        return _contain_adversarial(bundle, claim_risk=str(claim_risk))

    receipts = organ_receipts_from_bundle(bundle)
    validation = validate_organ_receipts(receipts)
    if not validation.get("all_valid"):
        unknown_organs = validation.get("unknown_organs", [])
        reason = REFUSED_UNKNOWN_ORGAN if unknown_organs else REFUSED_MISSING_ORGAN
        posture = create_metabolic_posture(
            metabolism_ref,
            tuple(r["receipt_id"] for r in receipts),
            "fail_closed",
            observed_at=observed_at,
            notes="organ receipt validation failed",
        )
        return {
            **advisory_only_marker(),
            "status": "fail_closed",
            "bundle_id": bundle.get("bundle_id"),
            "reason_code": reason,
            "metabolic_posture": posture.to_payload(),
            "validation": validation,
            "permission_granted": False,
            "emitted_events": ("MET_FAILED_CLOSED",),
        }

    missing = _missing_organs(bundle)
    if missing:
        posture = create_metabolic_posture(
            metabolism_ref,
            tuple(r["receipt_id"] for r in receipts),
            "fail_closed",
            observed_at=observed_at,
            notes=f"missing: {', '.join(missing)}",
        )
        return {
            **advisory_only_marker(),
            "status": "fail_closed",
            "bundle_id": bundle.get("bundle_id"),
            "reason_code": REFUSED_MISSING_ORGAN,
            "missing_organs": missing,
            "metabolic_posture": posture.to_payload(),
            "permission_granted": False,
            "emitted_events": ("MET_FAILED_CLOSED",),
        }

    if bundle.get("input_freshness") == "stale":
        posture = create_metabolic_posture(
            metabolism_ref,
            tuple(r["receipt_id"] for r in receipts),
            "fail_closed",
            observed_at=observed_at,
            notes="stale input",
        )
        return {
            **advisory_only_marker(),
            "status": "fail_closed",
            "bundle_id": bundle.get("bundle_id"),
            "reason_code": REFUSED_STALE_INPUT,
            "metabolic_posture": posture.to_payload(),
            "permission_granted": False,
            "emitted_events": ("MET_FAILED_CLOSED",),
        }

    cross_claims = tuple(bundle.get("cross_organ_claims", ()))
    tep_eval: dict[str, object] | None = None
    if cross_claims:
        tep_eval = _evaluate_cross_organ_claims(cross_claims)
        if not tep_eval.get("all_ok"):
            return {
                **_contain_adversarial(bundle, claim_risk="naked_scalar"),
                "tep_evaluation": tep_eval,
            }

    proposals_raw = tuple(bundle.get("proposals", ()))
    processed_proposals = _process_proposals(proposals_raw) if proposals_raw else []
    routes = _route_proposals_to_organs(processed_proposals)
    route_refs = tuple(r.route_id for r in routes)

    signals: list[MetabolicSignal] = []
    for receipt in receipts:
        organ = str(receipt["organ"])
        wrapped = wrap_organ_receipt(receipt, source_organ=organ)
        signal = MetabolicSignal(
            signal_id=_deterministic_id("met-signal", receipt["receipt_id"]),
            organ=organ,
            signal_kind="energy_state",
            observed_at=observed_at,
            payload_ref=str(receipt.get("payload_ref", "")),
            pressure_score=0.3,
        )
        signals.append(signal)

    organ_refs = tuple(s.signal_id for s in signals)
    posture_level = "stable" if not processed_proposals else "pressured"
    posture = create_metabolic_posture(
        metabolism_ref,
        organ_refs,
        posture_level,
        observed_at=observed_at,
        notes=notes,
    )

    events_list = [
        "MET_ENERGY_STATE_OBSERVED",
        MET_POSTURE_CREATED,
    ]
    for proposal in processed_proposals:
        if proposal.get("status") == "proposal":
            events_list.append(str(proposal.get("event", "MET_ENERGY_STATE_OBSERVED")))
    if routes:
        events_list.append("MET_ORGAN_ROUTE_CREATED")
    events_list.extend([MET_RECEIPT_CREATED, MET_METABOLIC_SUMMARY_RECORDED])
    events = tuple(dict.fromkeys(events_list))

    receipt = create_metabolic_receipt(
        metabolism_ref,
        posture,
        organ_refs,
        organ_route_refs=route_refs,
        emitted_events=events,
    )

    result: dict[str, object] = {
        **advisory_only_marker(),
        "status": "recorded",
        "bundle_id": bundle.get("bundle_id"),
        "observed_at": observed_at,
        "metabolic_posture": posture.to_payload(),
        "metabolic_receipt": receipt.to_payload(),
        "organ_signals": [s.to_payload() for s in signals],
        "proposals": processed_proposals,
        "permission_granted": False,
        "authority_created": False,
        "emitted_events": events,
    }
    if routes:
        result["organ_routes"] = [r.to_payload() for r in routes]
    if tep_eval is not None:
        result["tep_evaluation"] = tep_eval

    return attach_translation_envelope_to_result(
        result,
        source_organ="MET",
        claim_type="BOUNDARY_RECEIPT",
        receipt_key="metabolic_receipt",
    )


def refuse_met_as_authority(*, treat_as_authority: bool) -> None:
    from hg_core.met_cluster.errors import MetValidationError, REFUSED_MET_AS_AUTHORITY

    if treat_as_authority and met_refuse_authority_conversion():
        raise MetValidationError(REFUSED_MET_AS_AUTHORITY, "metabolic governance is not authority")


__all__ = [
    "create_metabolic_posture",
    "create_metabolic_receipt",
    "organ_receipts_from_bundle",
    "process_metabolic_bundle",
    "refuse_met_as_authority",
    "validate_organ_receipts",
]
