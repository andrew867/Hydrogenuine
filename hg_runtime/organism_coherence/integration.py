"""H8 cross-module fixture integration — consume boundary/DRB/TEP/A0-HM receipts."""

from __future__ import annotations

from typing import Any

from hg_core.h8_cluster.errors import (
    REFUSED_A0_HM_AS_AUTHORITY,
    REFUSED_BOUNDARY_CHAIN_AUTHORITY,
    REFUSED_DRB_AS_MEMORY,
    REFUSED_DRB_AS_PERMISSION,
    REFUSED_INCOMPLETE_MODULE_RECEIPT,
    REFUSED_TEP_AS_AUTHORITY,
)
from hg_core.h8_cluster.no_authority import advisory_only_marker
from hg_runtime.organism_coherence.types import OrganismModuleReceipt, module_receipt_from_fixture


def validate_module_receipt(receipt: OrganismModuleReceipt) -> dict[str, object]:
    """Validate a completed-module fixture receipt is advisory-only."""
    if receipt.status != "completed":
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": REFUSED_INCOMPLETE_MODULE_RECEIPT,
            "detail": f"organ {receipt.organ} status={receipt.status}",
            "permission_granted": False,
        }
    return {
        **advisory_only_marker(),
        "status": "accepted",
        "reason_code": "h8.advisory.module_receipt_validated",
        "receipt_id": receipt.receipt_id,
        "organ": receipt.organ,
        "permission_granted": False,
    }


def consume_drb_fixture_receipt(receipt_payload: dict[str, Any]) -> dict[str, object]:
    """Consume DRB fixture receipt — refuse permission/memory conversion."""
    treat_as = receipt_payload.get("treat_as")
    if treat_as in ("permission", "memory", "proof", "history"):
        code = REFUSED_DRB_AS_PERMISSION if treat_as == "permission" else REFUSED_DRB_AS_MEMORY
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": code,
            "detail": f"DRB fragment refused as {treat_as}",
            "permission_granted": False,
        }
    if receipt_payload.get("permission_granted") is True:
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": REFUSED_DRB_AS_PERMISSION,
            "permission_granted": False,
        }
    return {
        **advisory_only_marker(),
        "status": "accepted",
        "reason_code": "h8.advisory.drb_receipt_consumed",
        "not_permission": True,
        "not_memory": True,
        "permission_granted": False,
    }


def consume_tep_fixture_envelope(envelope_payload: dict[str, Any]) -> dict[str, object]:
    """Consume TEP envelope — authority_created must remain false."""
    authority = envelope_payload.get("authority_semantics", {})
    if isinstance(authority, dict):
        if authority.get("may_mint_permit") or authority.get("may_authorize_execution"):
            return {
                **advisory_only_marker(),
                "status": "refused",
                "reason_code": REFUSED_TEP_AS_AUTHORITY,
                "permission_granted": False,
            }
    if envelope_payload.get("authority_created") is True:
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": REFUSED_TEP_AS_AUTHORITY,
            "permission_granted": False,
        }
    return {
        **advisory_only_marker(),
        "status": "accepted",
        "reason_code": "h8.advisory.tep_envelope_consumed",
        "authority_created": False,
        "permission_granted": False,
    }


def consume_a0_hm_posture(posture_payload: dict[str, Any]) -> dict[str, object]:
    """Consume A0-HM posture — orientation only, never authority."""
    if posture_payload.get("treat_as_authority") is True:
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": REFUSED_A0_HM_AS_AUTHORITY,
            "permission_granted": False,
        }
    if posture_payload.get("permission_granted") is True or posture_payload.get("authority_created") is True:
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": REFUSED_A0_HM_AS_AUTHORITY,
            "permission_granted": False,
        }
    return {
        **advisory_only_marker(),
        "status": "accepted",
        "reason_code": "h8.advisory.a0_hm_posture_consumed",
        "posture_is_not_authority": True,
        "permission_granted": False,
    }


def consume_boundary_receipt_chain(chain: list[dict[str, Any]]) -> dict[str, object]:
    """Validate boundary receipt chain cannot launder authority."""
    for link in chain:
        if link.get("permission_granted") is True or link.get("authority_created") is True:
            return {
                **advisory_only_marker(),
                "status": "refused",
                "reason_code": REFUSED_BOUNDARY_CHAIN_AUTHORITY,
                "detail": f"chain link {link.get('receipt_id')} claims authority",
                "permission_granted": False,
            }
        if link.get("launders_authority") is True:
            return {
                **advisory_only_marker(),
                "status": "refused",
                "reason_code": REFUSED_BOUNDARY_CHAIN_AUTHORITY,
                "permission_granted": False,
            }
    return {
        **advisory_only_marker(),
        "status": "accepted",
        "reason_code": "h8.advisory.boundary_chain_consumed",
        "chain_length": len(chain),
        "permission_granted": False,
    }


def validate_fixture_receipts(receipts: tuple[OrganismModuleReceipt, ...]) -> dict[str, object]:
    results = [validate_module_receipt(r) for r in receipts]
    all_ok = all(r.get("status") == "accepted" for r in results)
    return {
        **advisory_only_marker(),
        "status": "validated" if all_ok else "refused",
        "results": results,
        "all_valid": all_ok,
        "permission_granted": False,
    }


def module_receipts_from_bundle(bundle: dict[str, Any]) -> tuple[OrganismModuleReceipt, ...]:
    raw = bundle.get("module_receipts", ())
    return tuple(module_receipt_from_fixture(dict(r)) for r in raw)


__all__ = [
    "consume_a0_hm_posture",
    "consume_boundary_receipt_chain",
    "consume_drb_fixture_receipt",
    "consume_tep_fixture_envelope",
    "module_receipts_from_bundle",
    "validate_fixture_receipts",
    "validate_module_receipt",
]
