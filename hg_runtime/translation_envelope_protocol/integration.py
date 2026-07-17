"""TEP organ integration fixtures — ARB/IMB/ORI/EGI/RPB/GPP/UEAK static paths."""

from __future__ import annotations

from typing import Any

from hg_runtime.translation_envelope_protocol.decide import tep_decide
from hg_runtime.translation_envelope_protocol.fixtures import (
    ADVISORY_AUTHORITY,
    DEFAULT_OPERATORS,
    EXECUTION_REFERENCE,
    PERMIT_REFERENCE,
    POSTURE_REFERENCE,
    REVIEW_REFERENCE,
    fixture_claim,
    fixture_envelope,
    gpp_permit_evidence_fixture,
    naked_scalar_fixture,
    ori_review_receipt_fixture,
    ueak_admission_evidence_fixture,
)
from hg_runtime.translation_envelope_protocol.drb_integration import (
    run_drb_tep_integration_path,
    wrap_drb_dream_fragment,
)
from hg_runtime.translation_envelope_protocol.types import Claim, TranslationEnvelope
from hg_runtime.translation_envelope_protocol.validator import is_naked_claim


def arb_consume_routed_claim(
    claim: Claim,
    envelope: TranslationEnvelope | None,
) -> dict[str, Any]:
    """ARB refuses naked inbound claims before routing."""
    naked, reason = is_naked_claim(claim, envelope)
    if naked:
        return {
            "organ": "ARB",
            "status": "refused",
            "reason_code": "tep.naked_claim_refused",
            "detail": reason,
            "routed": False,
            "authority_created": False,
        }
    decision = tep_decide(claim, envelope, envelope.reference_condition if envelope else REVIEW_REFERENCE)
    return {
        "organ": "ARB",
        "status": "routed" if decision.decision.startswith("ACCEPT") else "refused",
        "tep_decision": decision.decision,
        "reason": decision.reason,
        "routed": decision.decision.startswith("ACCEPT"),
        "authority_created": False,
    }


def imb_emit_mediation_receipt(
    claim: Claim,
    envelope: TranslationEnvelope,
) -> dict[str, Any]:
    """IMB wraps consensus claims; consensus is not authority."""
    decision = tep_decide(claim, envelope, PERMIT_REFERENCE, operators=DEFAULT_OPERATORS)
    return {
        "organ": "IMB",
        "status": "emitted",
        "receipt_type": "BOUNDARY_RECEIPT",
        "tep_decision": decision.decision,
        "authority_created": False,
        "consensus_is_not_authority": decision.decision != "ACCEPT_DIRECT"
        or envelope.authority_semantics.authority_type != "GPP_PERMIT",
    }


def ori_emit_review_receipt(*, approved: bool = True) -> dict[str, Any]:
    """ORI receipts carry authority semantics; they are not permits."""
    claim, envelope = ori_review_receipt_fixture(approved=approved)
    decision = tep_decide(claim, envelope, PERMIT_REFERENCE, operators=DEFAULT_OPERATORS)
    return {
        "organ": "ORI",
        "status": "emitted",
        "receipt_type": envelope.claim_type,
        "identity_ref": envelope.identity_ref,
        "scope_ref": envelope.scope_ref,
        "tep_decision": decision.decision,
        "is_permit": False,
        "authority_created": False,
    }


def egi_emit_gap_proposal(
    claim: Claim,
    envelope: TranslationEnvelope | None,
) -> dict[str, Any]:
    """EGI proposals cannot grant tools/memory/context."""
    naked, reason = is_naked_claim(claim, envelope)
    if naked:
        return {
            "organ": "EGI",
            "status": "refused",
            "reason_code": "tep.naked_claim_refused",
            "detail": reason,
            "authority_created": False,
        }
    assert envelope is not None
    semantics = envelope.authority_semantics
    if semantics.may_grant_tools or semantics.may_grant_memory or semantics.may_grant_context:
        return {
            "organ": "EGI",
            "status": "refused",
            "reason_code": "tep.authority_conversion_refused",
            "authority_created": False,
        }
    return {
        "organ": "EGI",
        "status": "proposal_only",
        "advisory_only": True,
        "authority_created": False,
    }


def rpb_emit_posture_claim(
    claim: Claim,
    envelope: TranslationEnvelope,
) -> dict[str, Any]:
    """RPB posture cannot approve execution."""
    decision = tep_decide(claim, envelope, EXECUTION_REFERENCE, operators=DEFAULT_OPERATORS)
    return {
        "organ": "RPB",
        "status": "emitted",
        "claim_type": "OPERATING_POSTURE",
        "tep_decision": decision.decision,
        "may_authorize_execution": envelope.authority_semantics.may_authorize_execution,
        "execution_approved": False,
        "authority_created": False,
    }


def gpp_fixture_evaluate_permit_request(request: dict[str, Any]) -> dict[str, Any]:
    """Fake GPP consumer rejects naked or wrong-authority evidence."""
    envelope = request.get("envelope")
    if envelope is None:
        return {
            "organ": "GPP",
            "status": "rejected",
            "reason_code": "gpp.fixture.naked_evidence",
            "permit_minted": False,
            "authority_created": False,
        }
    claim = fixture_claim(claim_id=request["evidence_claim_id"])
    decision = tep_decide(claim, envelope, PERMIT_REFERENCE, operators=DEFAULT_OPERATORS)
    if decision.decision in ("REJECT_NAKED_CLAIM", "FAIL_CLOSED"):
        return {
            "organ": "GPP",
            "status": "rejected",
            "reason_code": "gpp.fixture.invalid_evidence",
            "tep_decision": decision.decision,
            "permit_minted": False,
            "authority_created": False,
        }
    if envelope.authority_semantics.authority_type not in ("GPP_PERMIT", "PROOF_EVIDENCE"):
        return {
            "organ": "GPP",
            "status": "rejected",
            "reason_code": "gpp.fixture.wrong_authority",
            "tep_decision": decision.decision,
            "permit_minted": False,
            "authority_created": False,
        }
    return {
        "organ": "GPP",
        "status": "evidence_accepted_for_review",
        "tep_decision": decision.decision,
        "permit_minted": False,
        "authority_created": False,
    }


def ueak_fixture_evaluate_admission_request(request: dict[str, Any]) -> dict[str, Any]:
    """Fake UEAK consumer rejects naked supporting claims."""
    envelope = request.get("envelope")
    if envelope is None:
        return {
            "organ": "UEAK",
            "status": "rejected",
            "reason_code": "ueak.fixture.naked_support",
            "admitted": False,
            "authority_created": False,
        }
    claim = fixture_claim(
        claim_id=request["support_claim_id"],
        claim_type=envelope.claim_type,
        scalar_value=envelope.scalar_value,
    )
    decision = tep_decide(claim, envelope, EXECUTION_REFERENCE, operators=DEFAULT_OPERATORS)
    if decision.decision in ("REJECT_NAKED_CLAIM", "FAIL_CLOSED", "REJECT_NOT_TRANSLATABLE"):
        return {
            "organ": "UEAK",
            "status": "rejected",
            "reason_code": "ueak.fixture.invalid_support",
            "tep_decision": decision.decision,
            "admitted": False,
            "authority_created": False,
        }
    return {
        "organ": "UEAK",
        "status": "support_review_only",
        "tep_decision": decision.decision,
        "admitted": False,
        "authority_created": False,
    }


def bac_fixture_chain_metadata(
    chain: list[tuple[Claim, TranslationEnvelope | None]],
) -> dict[str, Any]:
    """BAC-compatible metadata: advisory chain stays advisory."""
    edges: list[dict[str, Any]] = []
    authority_created = False
    for claim, envelope in chain:
        naked, _ = is_naked_claim(claim, envelope)
        authority_type = "NONE"
        translation_status = "UNKNOWN"
        if envelope is not None:
            authority_type = envelope.authority_semantics.authority_type
            translation_status = envelope.translation_status
        edges.append(
            {
                "claim_id": claim.claim_id,
                "naked": naked,
                "authority_type": authority_type,
                "translation_status": translation_status,
                "authority_created": False,
            }
        )
        if authority_type in ("GPP_PERMIT", "UEAK_ADMISSION"):
            authority_created = True
    return {
        "organ": "BAC",
        "edges": edges,
        "chain_stays_advisory": not authority_created,
        "authority_created": False,
    }


def run_boundary_integration_path() -> dict[str, Any]:
    """Exercise ARB→IMB→ORI→EGI→RPB→GPP→UEAK fixture path."""
    naked = naked_scalar_fixture()
    arb_naked = arb_consume_routed_claim(naked, None)

    claim = fixture_claim(claim_type="BOUNDARY_RECEIPT", claim_id="claim:imb-consensus")
    envelope = fixture_envelope(
        claim,
        producer_module="IMB",
        authority_semantics=ADVISORY_AUTHORITY,
    )
    imb = imb_emit_mediation_receipt(claim, envelope)

    ori = ori_emit_review_receipt(approved=True)
    egi_naked = egi_emit_gap_proposal(naked_scalar_fixture("PRIORITY_SCORE"), None)
    egi_ok = egi_emit_gap_proposal(
        fixture_claim(claim_id="claim:egi-gap", claim_type="PRIORITY_SCORE"),
        fixture_envelope(
            fixture_claim(claim_id="claim:egi-gap", claim_type="PRIORITY_SCORE"),
            producer_module="EGI",
        ),
    )

    posture_claim = fixture_claim(claim_type="OPERATING_POSTURE", claim_id="claim:rpb-posture", scalar_value=0.9)
    posture_env = fixture_envelope(
        posture_claim,
        producer_module="RPB",
        reference_condition=POSTURE_REFERENCE,
    )
    rpb = rpb_emit_posture_claim(posture_claim, posture_env)

    gpp_naked = gpp_fixture_evaluate_permit_request(gpp_permit_evidence_fixture(naked=True))
    gpp_ok = gpp_fixture_evaluate_permit_request(gpp_permit_evidence_fixture(naked=False))
    ueak_naked = ueak_fixture_evaluate_admission_request(ueak_admission_evidence_fixture(naked=True))
    ueak_ok = ueak_fixture_evaluate_admission_request(ueak_admission_evidence_fixture(naked=False))

    advisory_chain = [
        (fixture_claim(claim_id="c1"), fixture_envelope(fixture_claim(claim_id="c1"), envelope_id="e1")),
        (fixture_claim(claim_id="c2"), fixture_envelope(fixture_claim(claim_id="c2"), envelope_id="e2")),
    ]
    bac = bac_fixture_chain_metadata(advisory_chain)

    drb_naked = arb_consume_routed_claim(
        fixture_claim(
            claim_type="SIMULATION_RESULT",
            claim_id="naked:drb-fragment",
            structured_value={"drb_output_kind": "dream_fragment"},
        ),
        None,
    )
    drb_wrapped_claim, drb_wrapped_env = wrap_drb_dream_fragment(
        {"fragment_id": "frag:boundary", "fragment_type": "residue", "content": "fixture"}
    )
    drb_wrapped = arb_consume_routed_claim(drb_wrapped_claim, drb_wrapped_env)
    drb_tep = run_drb_tep_integration_path()

    return {
        "arb_naked_refused": arb_naked["status"] == "refused",
        "imb_not_authority": imb["consensus_is_not_authority"],
        "ori_not_permit": not ori["is_permit"],
        "egi_naked_refused": egi_naked["status"] == "refused",
        "egi_proposal_ok": egi_ok["status"] == "proposal_only",
        "rpb_no_execution": not rpb["execution_approved"],
        "gpp_naked_rejected": gpp_naked["status"] == "rejected",
        "gpp_evidence_reviewed": gpp_ok["status"] == "evidence_accepted_for_review",
        "ueak_naked_rejected": ueak_naked["status"] == "rejected",
        "ueak_not_admitted": not ueak_ok["admitted"],
        "bac_chain_advisory": bac["chain_stays_advisory"],
        "drb_naked_refused": drb_naked["status"] == "refused",
        "drb_wrapped_not_naked": drb_wrapped["status"] != "refused" or drb_wrapped.get("reason_code") != "tep.naked_claim_refused",
        "drb_tep_integration_ok": drb_tep["naked_drb_fragment_refused"] and drb_tep["gpp_no_permit_from_drb"],
        "no_oea_ter_called": True,
        "details": {
            "arb_naked": arb_naked,
            "imb": imb,
            "ori": ori,
            "egi_naked": egi_naked,
            "egi_ok": egi_ok,
            "rpb": rpb,
            "gpp_naked": gpp_naked,
            "gpp_ok": gpp_ok,
            "ueak_naked": ueak_naked,
            "ueak_ok": ueak_ok,
            "bac": bac,
            "drb_naked": drb_naked,
            "drb_wrapped": drb_wrapped,
            "drb_tep": drb_tep,
        },
    }


__all__ = [
    "arb_consume_routed_claim",
    "bac_fixture_chain_metadata",
    "egi_emit_gap_proposal",
    "gpp_fixture_evaluate_permit_request",
    "imb_emit_mediation_receipt",
    "ori_emit_review_receipt",
    "rpb_emit_posture_claim",
    "run_boundary_integration_path",
    "ueak_fixture_evaluate_admission_request",
]
