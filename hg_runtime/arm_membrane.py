"""ARM membrane TEP validation — shared across AIS/IMS/MBS/OEF/NRV."""

from __future__ import annotations

from typing import Any

from hg_core.tep_cluster.no_authority import advisory_only_marker
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
from hg_runtime.translation_envelope_protocol.types import AuthoritySemantics, Claim, TranslationEnvelope
from hg_runtime.translation_envelope_protocol.validator import is_naked_claim, validate_translation_envelope


def _claim_from_tep_data(data: dict[str, Any]) -> Claim:
    return fixture_claim(
        claim_type=data.get("claim_type", "BOUNDARY_RECEIPT"),  # type: ignore[arg-type]
        claim_id=str(data.get("claim_id", "claim:arm:fixture")),
        structured_value=dict(data.get("structured_value", {})),
    )


def _reference_for_claim(claim: Claim):
    if claim.claim_type == "RISK_SCORE":
        return PRIORITY_REFERENCE
    return PROPOSAL_REFERENCE


def _envelope_from_tep_data(data: dict[str, Any], claim: Claim) -> TranslationEnvelope | None:
    env_data = data.get("envelope")
    if not isinstance(env_data, dict):
        return None
    authority_data = env_data.get("authority_semantics", {})
    authority = ADVISORY_AUTHORITY
    if isinstance(authority_data, dict):
        authority = AuthoritySemantics(
            authority_type=authority_data.get("authority_type", "ADVISORY"),  # type: ignore[arg-type]
            may_authorize_execution=bool(authority_data.get("may_authorize_execution", False)),
            may_mint_permit=bool(authority_data.get("may_mint_permit", False)),
            may_call_oea_ter=False,
            may_grant_tools=False,
            may_grant_memory=False,
            may_grant_context=False,
            may_publish=False,
            downstream_allowed_uses=("prioritization", "observation"),
            downstream_forbidden_uses=("permit evidence", "execution input"),
            required_authority_chain_refs=(),
        )
    return fixture_envelope(
        claim,
        envelope_id=str(env_data.get("envelope_id", f"env:arm:{claim.claim_id}")),
        producer_module=str(env_data.get("producer_module", "ARM")),
        reference_condition=_reference_for_claim(claim),
        observation_envelope=FIXTURE_OBSERVATION,
        uncertainty_semantics=HEURISTIC_UNCERTAINTY,
        authority_semantics=authority,
        translation_status=env_data.get("translation_status", "DIRECTLY_COMPARABLE"),  # type: ignore[arg-type]
        expires_at=str(env_data.get("ttl_expires_at", env_data.get("expires_at", "2026-06-15T22:30:00.000000Z"))),
    )


def validate_membrane_crossing(
    bundle: dict[str, Any],
    *,
    observed_at: str,
    refused_missing_tep: str,
    refused_ttl_expired: str = "",
    refused_authority_bearing: str = "",
) -> dict[str, object] | None:
    """Return fail_closed dict when membrane crossing is invalid; None when OK or not crossing."""
    if not bundle.get("crosses_membrane") and not bundle.get("tep_required"):
        return None
    tep_data = bundle.get("tep_envelope")
    if not isinstance(tep_data, dict):
        return {
            **advisory_only_marker(),
            "status": "fail_closed",
            "bundle_id": bundle.get("bundle_id"),
            "reason_code": refused_missing_tep,
            "permission_granted": False,
            "emitted_events": ("ARM_MEMBRANE_FAILED_CLOSED",),
            "tep_validation": {"ok": False, "detail": "missing tep_envelope"},
        }
    auth = tep_data.get("envelope", {}).get("authority_semantics", {})
    if refused_authority_bearing and isinstance(auth, dict):
        if auth.get("may_authorize_execution") or auth.get("may_mint_permit"):
            return {
                **advisory_only_marker(),
                "status": "fail_closed",
                "bundle_id": bundle.get("bundle_id"),
                "reason_code": refused_authority_bearing,
                "permission_granted": False,
                "emitted_events": ("ARM_MEMBRANE_FAILED_CLOSED",),
                "tep_validation": {"ok": False, "detail": "authority-bearing envelope"},
            }
    claim = _claim_from_tep_data(tep_data)
    envelope = _envelope_from_tep_data(tep_data, claim)
    if envelope is None:
        return {
            **advisory_only_marker(),
            "status": "fail_closed",
            "bundle_id": bundle.get("bundle_id"),
            "reason_code": refused_missing_tep,
            "permission_granted": False,
            "emitted_events": ("ARM_MEMBRANE_FAILED_CLOSED",),
            "tep_validation": {"ok": False, "detail": "invalid envelope"},
        }
    naked, naked_reason = is_naked_claim(claim, envelope)
    if naked:
        return {
            **advisory_only_marker(),
            "status": "fail_closed",
            "bundle_id": bundle.get("bundle_id"),
            "reason_code": refused_missing_tep,
            "permission_granted": False,
            "emitted_events": ("ARM_MEMBRANE_FAILED_CLOSED",),
            "tep_validation": {"ok": False, "detail": naked_reason},
        }
    ttl = str(
        tep_data.get("envelope", {}).get(
            "ttl_expires_at",
            tep_data.get("envelope", {}).get("expires_at", "2026-06-15T22:30:00.000000Z"),
        )
    )
    if refused_ttl_expired and ttl < observed_at:
        return {
            **advisory_only_marker(),
            "status": "fail_closed",
            "bundle_id": bundle.get("bundle_id"),
            "reason_code": refused_ttl_expired,
            "permission_granted": False,
            "emitted_events": ("ARM_MEMBRANE_FAILED_CLOSED",),
            "tep_validation": {"ok": False, "detail": "ttl expired"},
        }
    try:
        validate_translation_envelope(envelope)
    except Exception as exc:  # noqa: BLE001
        return {
            **advisory_only_marker(),
            "status": "fail_closed",
            "bundle_id": bundle.get("bundle_id"),
            "reason_code": refused_missing_tep,
            "permission_granted": False,
            "emitted_events": ("ARM_MEMBRANE_FAILED_CLOSED",),
            "tep_validation": {"ok": False, "detail": str(exc)},
        }
    decision = tep_decide(claim, envelope, _reference_for_claim(claim))
    accepted = decision.decision.startswith("ACCEPT") or decision.decision == "ROUTE_TO_REVIEW"
    if not accepted:
        return {
            **advisory_only_marker(),
            "status": "fail_closed",
            "bundle_id": bundle.get("bundle_id"),
            "reason_code": refused_missing_tep,
            "permission_granted": False,
            "emitted_events": ("ARM_MEMBRANE_FAILED_CLOSED",),
            "tep_validation": {"ok": False, "tep_decision": decision.decision},
        }
    return None


__all__ = ["validate_membrane_crossing"]
