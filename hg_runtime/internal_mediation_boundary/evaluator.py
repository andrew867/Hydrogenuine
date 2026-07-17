"""IMB evaluator — internal mediation is not permission."""

from __future__ import annotations

from typing import Any

from hg_core.imb_cluster.config import imb_refuse_authority_conversion
from hg_core.imb_cluster.errors import (
    IMB_CLAIM_RECORDED,
    IMB_SIGNAL_REFUSED,
    REFUSED_FORBIDDEN_CLAIM,
    REFUSED_IMB_AS_AUTHORITY,
    ImbValidationError,
)
from hg_core.imb_cluster.evaluation import resolve_risk_containment
from hg_core.imb_cluster.no_authority import advisory_only_marker
from hg_core.policy_safety.hashing import canonical_hash
from hg_runtime.internal_mediation_boundary.detector import detect_internal_conflicts
from hg_runtime.internal_mediation_boundary.events import mediation_selection_event
from hg_runtime.internal_mediation_boundary.fixtures import claims_from_bundle, load_fixture_bundles
from hg_runtime.internal_mediation_boundary.mediator import mediate_internal_conflict, refuse_consensus_as_authority
from hg_runtime.internal_mediation_boundary.policies import load_static_mediation_policies
from hg_runtime.internal_mediation_boundary.types import (
    FIXTURE_CLOCK,
    InternalConflict,
    InternalModuleClaim,
    MediationReceipt,
    classify_claim_risk,
    module_claim_from_fixture,
)

_RISK_REASON = {
    "forbidden_claim": REFUSED_FORBIDDEN_CLAIM,
    "consensus_as_authority": "imb.refused.consensus_as_authority",
    "authority_conversion": "imb.contained.authority_conversion",
}
_ADVISORY_CONTAINMENT_WAIVED_IMB = "imb.advisory.containment_waived"


def refuse_imb_as_authority(*, treat_as_authority: bool) -> None:
    if treat_as_authority:
        raise ImbValidationError(REFUSED_IMB_AS_AUTHORITY, "internal mediation cannot become authority")


def _deterministic_id(prefix: str, *parts: str) -> str:
    digest = canonical_hash({"prefix": prefix, "parts": list(parts)})
    return f"{prefix}-{digest.rsplit(':', 1)[-1][:12]}"


def _emit_events(*codes: str) -> tuple[str, ...]:
    return tuple(dict.fromkeys(codes))


def record_module_claim(
    claim: InternalModuleClaim,
    *,
    treat_as_authority: bool = False,
) -> dict[str, object]:
    if treat_as_authority:
        refuse_imb_as_authority(treat_as_authority=True)

    risk = classify_claim_risk(claim.claim_summary)
    contained = resolve_risk_containment(
        risk=risk,
        risk_reason_map=_RISK_REASON,
        waived_reason_code=_ADVISORY_CONTAINMENT_WAIVED_IMB,
        payload={"claim_id": claim.claim_id, "mediation_is_advisory_only": True},
        refuse_for_risk=lambda kind: imb_refuse_authority_conversion()
        if kind in ("authority_conversion", "consensus_as_authority")
        else True,
    )
    if contained is not None:
        status = "contained" if contained.get("containment_active") else "recorded"
        return {
            **contained,
            "status": status,
            "claim": claim.to_payload(),
            "emitted_events": _emit_events("IMB_INTERNAL_MODULE_CLAIM_RECORDED", "IMB_AUTHORITY_CONVERSION_CONTAINED"),
        }

    if claim.source_module == "unknown" and claim.claim_type == "unknown":
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": IMB_SIGNAL_REFUSED,
            "claim_id": claim.claim_id,
            "claim": claim.to_payload(),
            "emitted_events": _emit_events("IMB_SIGNAL_REFUSED"),
        }

    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": IMB_CLAIM_RECORDED,
        "claim_id": claim.claim_id,
        "claim": claim.to_payload(),
        "emitted_events": _emit_events("IMB_INTERNAL_MODULE_CLAIM_RECORDED"),
        "mediation_is_advisory_only": True,
    }


def mediate_claim_bundle(
    claims: tuple[InternalModuleClaim, ...],
    *,
    observed_at: str = FIXTURE_CLOCK,
    policies: tuple[Any, ...] | None = None,
) -> dict[str, object]:
    consensus = refuse_consensus_as_authority(claims)
    if consensus is not None:
        return {
            **consensus,
            "emitted_events": _emit_events("IMB_INTERNAL_CONSENSUS_REFUSED_AS_AUTHORITY"),
        }

    active_policies = policies if policies is not None else load_static_mediation_policies()
    recorded = [record_module_claim(c) for c in claims]
    claims_by_id = {c.claim_id: c for c in claims}

    detection = detect_internal_conflicts(claims, detected_at=observed_at)
    conflict_payloads = list(detection.get("conflicts", []))
    mediations: list[dict[str, object]] = []
    receipts: list[dict[str, object]] = []
    events: list[str] = ["IMB_INTERNAL_MODULE_CLAIM_RECORDED"]

    if conflict_payloads:
        events.append("IMB_INTERNAL_CONFLICT_DETECTED")

    for payload in conflict_payloads:
        conflict = InternalConflict(
            conflict_id=str(payload["conflict_id"]),
            claim_refs=tuple(payload["claim_refs"]),
            conflict_type=payload["conflict_type"],  # type: ignore[arg-type]
            conflict_summary=str(payload["conflict_summary"]),
            evidence_refs=tuple(payload.get("evidence_refs", [])),
            detected_at=str(payload.get("detected_at", observed_at)),
        )
        result = mediate_internal_conflict(
            conflict,
            claims_by_id,
            policies=active_policies,  # type: ignore[arg-type]
            observed_at=observed_at,
        )
        mediations.append(result)
        events.append("IMB_MEDIATION_POLICY_APPLIED")
        events.append("IMB_MEDIATION_DECISION_RECORDED")
        selection = mediation_selection_event(str(result.get("selected_resolution", "")))
        if selection:
            events.append(selection)
        decision_payload = result.get("decision")
        if isinstance(decision_payload, dict):
            receipt = MediationReceipt(
                receipt_id=_deterministic_id("imb-receipt", conflict.conflict_id),
                conflict_ref=f"imb:{conflict.conflict_id}",
                mediation_decision_ref=f"imb:{decision_payload['mediation_id']}",
                emitted_events=tuple(events),
            )
            MediationReceipt.validate_negative_proofs(receipt.to_payload())
            receipts.append(receipt.to_payload())
            events.append("IMB_MEDIATION_RECEIPT_CREATED")

    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": "imb.advisory.bundle_mediation_complete",
        "recorded_claims": recorded,
        "detection": detection,
        "mediations": mediations,
        "receipts": receipts,
        "emitted_events": _emit_events(*events),
        "mediation_is_advisory_only": True,
        "permission_granted": False,
        "all_preserved": all(
            len(m.get("decision", {}).get("preserved_claim_refs", [])) >= 2  # type: ignore[union-attr]
            for m in mediations
            if isinstance(m.get("decision"), dict)
        )
        if mediations
        else True,
    }


def analyze_fixture_bundles(
    bundles: tuple[dict[str, Any], ...] | None = None,
    *,
    observed_at: str = FIXTURE_CLOCK,
) -> dict[str, object]:
    active = bundles if bundles is not None else load_fixture_bundles()
    results: list[dict[str, object]] = []
    for bundle in active:
        claims = claims_from_bundle(bundle)
        results.append(
            {
                "bundle_id": bundle.get("bundle_id"),
                "result": mediate_claim_bundle(claims, observed_at=observed_at),
            }
        )
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": "imb.advisory.fixture_bundles_analyzed",
        "fixture_analysis_only": True,
        "bundle_results": results,
        "bundle_count": len(results),
        "mediation_is_advisory_only": True,
        "all_advisory": all(
            r["result"].get("permission_granted") is False  # type: ignore[index]
            for r in results
        ),
    }


def replay_fixture_stream(
    fixtures: list[dict[str, Any]],
    *,
    observed_at: str = FIXTURE_CLOCK,
) -> tuple[list[dict[str, object]], str]:
    claims = tuple(module_claim_from_fixture(row) for row in fixtures)
    results: list[dict[str, object]] = []
    hashes: list[str] = []
    for claim in claims:
        result = record_module_claim(claim)
        results.append(result)
        claim_payload = result.get("claim")
        if isinstance(claim_payload, dict):
            hashes.append(str(claim_payload.get("record_hash", "")))
    combined = "|".join(hashes)
    return results, canonical_hash({"replay": combined})


__all__ = [
    "analyze_fixture_bundles",
    "mediate_claim_bundle",
    "record_module_claim",
    "refuse_imb_as_authority",
    "replay_fixture_stream",
]
