"""H8 evaluator — whole-organism coherence is not authority."""

from __future__ import annotations

from typing import Any

from hg_core.h8_cluster.config import h8_refuse_authority_conversion
from hg_core.h8_cluster.errors import (
    H8_AUTHORITY_CONVERSION_CONTAINED,
    H8_COHERENCE_RECEIPT_CREATED,
    H8_CONFLICT_ROUTED,
    H8_ORGANISM_COHERENCE_RECORDED,
    H8_ORGANISM_STATE_SUMMARY_CREATED,
    H8_UNKNOWN_ORGANISM_FAILED_CLOSED,
    REFUSED_A0_HM_AS_AUTHORITY,
    REFUSED_BOUNDARY_CHAIN_AUTHORITY,
    REFUSED_DRB_AS_MEMORY,
    REFUSED_DRB_AS_PERMISSION,
    REFUSED_FORBIDDEN_ORGANISM_CLAIM,
    REFUSED_MISSING_ORGAN,
    REFUSED_NAKED_SCALAR,
    REFUSED_STALE_APPROVAL,
    REFUSED_TEP_AS_AUTHORITY,
    REFUSED_UNKNOWN_ORGAN,
)
from hg_core.h8_cluster.no_authority import advisory_only_marker
from hg_core.policy_safety.hashing import canonical_hash
from hg_runtime.organism_coherence.conflict_route import route_conflicts
from hg_runtime.organism_coherence.events import adversarial_selection_event, conflict_route_event
from hg_runtime.organism_coherence.integration import (
    consume_a0_hm_posture,
    consume_boundary_receipt_chain,
    consume_drb_fixture_receipt,
    consume_tep_fixture_envelope,
    module_receipts_from_bundle,
    validate_fixture_receipts,
)
from hg_runtime.organism_coherence.types import (
    FIXTURE_CLOCK,
    REQUIRED_ORGANS,
    OrganismCoherenceReceipt,
    OrganismStateSummary,
    classify_organism_claim_risk,
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
from hg_runtime.translation_envelope_protocol.types import Claim, ReferenceCondition, TranslationEnvelope
from hg_runtime.translation_envelope_protocol.validator import is_naked_claim


_CLAIM_RISK_REASON: dict[str, str] = {
    "drb_as_permission": REFUSED_DRB_AS_PERMISSION,
    "drb_as_memory": REFUSED_DRB_AS_MEMORY,
    "tep_as_authority": REFUSED_TEP_AS_AUTHORITY,
    "a0_hm_as_authority": REFUSED_A0_HM_AS_AUTHORITY,
    "boundary_chain_authority": REFUSED_BOUNDARY_CHAIN_AUTHORITY,
    "naked_scalar": REFUSED_NAKED_SCALAR,
    "missing_organ": REFUSED_MISSING_ORGAN,
    "stale_approval": REFUSED_STALE_APPROVAL,
    "authority_conversion": H8_AUTHORITY_CONVERSION_CONTAINED,
    "forbidden_claim": REFUSED_FORBIDDEN_ORGANISM_CLAIM,
}


def _deterministic_id(prefix: str, *parts: str) -> str:
    digest = canonical_hash({"prefix": prefix, "parts": list(parts)})
    return f"{prefix}-{digest.rsplit(':', 1)[-1][:12]}"


def _present_organs(bundle: dict[str, Any]) -> set[str]:
    receipts = module_receipts_from_bundle(bundle)
    return {r.organ for r in receipts if r.status == "completed"}


def _missing_organs(bundle: dict[str, Any]) -> tuple[str, ...]:
    required = tuple(bundle.get("required_organs", REQUIRED_ORGANS))
    present = _present_organs(bundle)
    return tuple(o for o in required if o not in present)


def _claim_from_fixture(data: dict[str, Any]) -> Claim:
    return fixture_claim(
        claim_type=data.get("claim_type", "BOUNDARY_RECEIPT"),  # type: ignore[arg-type]
        claim_id=str(data.get("claim_id", "claim:h8-fixture")),
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
        producer_module=str(data.get("producer_module", "H8")),
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


def _contain_adversarial(
    bundle: dict[str, Any],
    *,
    claim_risk: str,
) -> dict[str, object]:
    reason_code = _CLAIM_RISK_REASON.get(claim_risk, REFUSED_FORBIDDEN_ORGANISM_CLAIM)
    event = adversarial_selection_event(claim_risk)
    return {
        **advisory_only_marker(),
        "status": "contained",
        "bundle_id": bundle.get("bundle_id"),
        "reason_code": reason_code,
        "claim_risk": claim_risk,
        "permission_granted": False,
        "emitted_events": (event, "H8_AUTHORITY_CONVERSION_CONTAINED"),
    }


def create_organism_state_summary(
    organism_ref: str,
    organ_refs: tuple[str, ...],
    coherence_status: str,
    *,
    conflict_route_refs: tuple[str, ...] = (),
    observed_at: str = FIXTURE_CLOCK,
    notes: str = "",
) -> OrganismStateSummary:
    return OrganismStateSummary(
        summary_id=_deterministic_id("h8-summary", organism_ref),
        organism_ref=organism_ref,
        organ_refs=organ_refs,
        coherence_status=coherence_status,  # type: ignore[arg-type]
        conflict_route_refs=conflict_route_refs,
        observed_at=observed_at,
        notes=notes,
    )


def create_coherence_receipt(
    organism_ref: str,
    summary: OrganismStateSummary,
    module_receipt_refs: tuple[str, ...],
    *,
    conflict_route_refs: tuple[str, ...] = (),
    emitted_events: tuple[str, ...],
) -> OrganismCoherenceReceipt:
    return OrganismCoherenceReceipt(
        receipt_id=_deterministic_id("h8-receipt", organism_ref),
        organism_ref=organism_ref,
        summary_ref=summary.summary_id,
        module_receipt_refs=module_receipt_refs,
        conflict_route_refs=conflict_route_refs,
        emitted_events=emitted_events,
    )


def process_organism_bundle(
    bundle: dict[str, Any],
    *,
    observed_at: str = FIXTURE_CLOCK,
) -> dict[str, object]:
    organism_ref, required_organs, notes = (
        str(bundle.get("organism_ref", "h8:fixture")),
        tuple(bundle.get("required_organs", REQUIRED_ORGANS)),
        str(bundle.get("notes", "")),
    )

    adversarial_signal = bundle.get("adversarial_signal")
    claim_risk = adversarial_signal or classify_organism_claim_risk(notes)
    if claim_risk and h8_refuse_authority_conversion():
        if claim_risk == "missing_organ":
            missing = _missing_organs(bundle)
            if missing:
                summary = create_organism_state_summary(
                    organism_ref,
                    tuple(r.receipt_id for r in module_receipts_from_bundle(bundle)),
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
                    "organism_state_summary": summary.to_payload(),
                    "permission_granted": False,
                    "emitted_events": ("H8_MISSING_ORGAN_FAILED_CLOSED",),
                }
        if claim_risk == "stale_approval":
            summary = create_organism_state_summary(
                organism_ref,
                tuple(r.receipt_id for r in module_receipts_from_bundle(bundle)),
                "fail_closed",
                observed_at=observed_at,
                notes="stale approval",
            )
            return {
                **advisory_only_marker(),
                "status": "fail_closed",
                "bundle_id": bundle.get("bundle_id"),
                "reason_code": REFUSED_STALE_APPROVAL,
                "stale_approval_refs": bundle.get("stale_approval_refs"),
                "organism_state_summary": summary.to_payload(),
                "permission_granted": False,
                "emitted_events": ("H8_STALE_APPROVAL_FAILED_CLOSED",),
            }
        if claim_risk == "naked_scalar":
            claims = tuple(bundle.get("cross_organ_claims", ()))
            eval_result = _evaluate_cross_organ_claims(claims)
            return {
                **_contain_adversarial(bundle, claim_risk="naked_scalar"),
                "tep_evaluation": eval_result,
            }
        if claim_risk in ("drb_as_permission", "drb_as_memory"):
            drb_payload = dict(bundle.get("drb_receipt", {}))
            drb_result = consume_drb_fixture_receipt(drb_payload)
            return {**_contain_adversarial(bundle, claim_risk=str(claim_risk)), "drb_consumption": drb_result}
        if claim_risk == "tep_as_authority":
            tep_payload = dict(bundle.get("tep_envelope", {}))
            tep_result = consume_tep_fixture_envelope(tep_payload)
            return {**_contain_adversarial(bundle, claim_risk="tep_as_authority"), "tep_consumption": tep_result}
        if claim_risk == "a0_hm_as_authority":
            posture = dict(bundle.get("a0_hm_posture", {}))
            a0_result = consume_a0_hm_posture(posture)
            return {**_contain_adversarial(bundle, claim_risk="a0_hm_as_authority"), "a0_hm_consumption": a0_result}
        if claim_risk == "boundary_chain_authority":
            chain = list(bundle.get("boundary_chain", ()))
            chain_result = consume_boundary_receipt_chain(chain)
            return {
                **_contain_adversarial(bundle, claim_risk="boundary_chain_authority"),
                "boundary_chain_consumption": chain_result,
            }
        return _contain_adversarial(bundle, claim_risk=str(claim_risk))

    receipts = module_receipts_from_bundle(bundle)
    validation = validate_fixture_receipts(receipts)
    if not validation.get("all_valid"):
        unknown_organs = [r.organ for r in receipts if r.status in ("unknown", "incomplete")]
        reason = REFUSED_UNKNOWN_ORGAN if unknown_organs else REFUSED_MISSING_ORGAN
        summary = create_organism_state_summary(
            organism_ref,
            tuple(r.receipt_id for r in receipts),
            "fail_closed",
            observed_at=observed_at,
            notes="module receipt validation failed",
        )
        return {
            **advisory_only_marker(),
            "status": "fail_closed",
            "bundle_id": bundle.get("bundle_id"),
            "reason_code": reason,
            "organism_state_summary": summary.to_payload(),
            "validation": validation,
            "permission_granted": False,
            "emitted_events": ("H8_UNKNOWN_ORGANISM_FAILED_CLOSED",),
        }

    missing = _missing_organs(bundle)
    if missing:
        summary = create_organism_state_summary(
            organism_ref,
            tuple(r.receipt_id for r in receipts),
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
            "organism_state_summary": summary.to_payload(),
            "permission_granted": False,
            "emitted_events": ("H8_MISSING_ORGAN_FAILED_CLOSED",),
        }

    if bundle.get("approval_freshness") == "stale":
        summary = create_organism_state_summary(
            organism_ref,
            tuple(r.receipt_id for r in receipts),
            "fail_closed",
            observed_at=observed_at,
            notes="stale approval",
        )
        return {
            **advisory_only_marker(),
            "status": "fail_closed",
            "bundle_id": bundle.get("bundle_id"),
            "reason_code": REFUSED_STALE_APPROVAL,
            "organism_state_summary": summary.to_payload(),
            "permission_granted": False,
            "emitted_events": ("H8_STALE_APPROVAL_FAILED_CLOSED",),
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

    conflict_specs = list(bundle.get("conflicts", ()))
    routes = route_conflicts(conflict_specs) if conflict_specs else ()
    coherence_status = "conflict_routed" if routes else "coherent"
    route_refs = tuple(r.route_id for r in routes)

    organ_refs = tuple(r.receipt_id for r in receipts)
    summary = create_organism_state_summary(
        organism_ref,
        organ_refs,
        coherence_status,
        conflict_route_refs=route_refs,
        observed_at=observed_at,
        notes=notes,
    )

    events_list = [
        "H8_ORGANISM_STATE_SUMMARY_CREATED",
        H8_ORGANISM_STATE_SUMMARY_CREATED,
    ]
    if routes:
        for route in routes:
            events_list.append(conflict_route_event(route.route_target))
        events_list.append(H8_CONFLICT_ROUTED)
    events_list.extend(
        [
            H8_COHERENCE_RECEIPT_CREATED,
            H8_ORGANISM_COHERENCE_RECORDED,
        ]
    )
    events = tuple(dict.fromkeys(events_list))

    receipt = create_coherence_receipt(
        organism_ref,
        summary,
        organ_refs,
        conflict_route_refs=route_refs,
        emitted_events=events,
    )

    result: dict[str, object] = {
        **advisory_only_marker(),
        "status": "recorded" if coherence_status == "coherent" else "conflict_routed",
        "bundle_id": bundle.get("bundle_id"),
        "observed_at": observed_at,
        "organism_state_summary": summary.to_payload(),
        "coherence_receipt": receipt.to_payload(),
        "module_receipts": [r.to_payload() for r in receipts],
        "permission_granted": False,
        "authority_created": False,
        "emitted_events": events,
    }
    if routes:
        result["conflict_routes"] = [r.to_payload() for r in routes]
    if tep_eval is not None:
        result["tep_evaluation"] = tep_eval
    return result


def refuse_h8_as_authority(*, treat_as_authority: bool) -> None:
    from hg_core.h8_cluster.errors import H8ValidationError, REFUSED_H8_AS_AUTHORITY

    if treat_as_authority and h8_refuse_authority_conversion():
        raise H8ValidationError(REFUSED_H8_AS_AUTHORITY, "organism coherence is not authority")


__all__ = [
    "create_coherence_receipt",
    "create_organism_state_summary",
    "process_organism_bundle",
    "refuse_h8_as_authority",
]
