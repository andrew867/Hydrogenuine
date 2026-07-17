"""Domain boundary refusal handling."""

from __future__ import annotations

from hg_runtime.domain_pack_runtime.domain_pack_record import build_domain_pack_boundary_record


FORBIDDEN_BOUNDARY_TAGS = frozenset({
    "deployment_permit",
    "authority_grant",
    "tool_authorization",
    "live_effects_enabled",
})


def detect_boundary_refusal(pack: dict) -> tuple[bool, list[str]]:
    reasons = []
    tags = set(pack.get("boundary_tags") or [])
    for forbidden in FORBIDDEN_BOUNDARY_TAGS:
        if forbidden in tags:
            reasons.append(f"forbidden_boundary_tag:{forbidden}")
    if not pack.get("provenance_refs"):
        reasons.append("missing_provenance_refs")
    return bool(reasons), reasons


def build_boundary_record_for_pack(pack: dict) -> dict:
    refused, reasons = detect_boundary_refusal(pack)
    return build_domain_pack_boundary_record(
        boundary_id=f"boundary-{pack['pack_id']}",
        pack_id=pack["pack_id"],
        boundary_tags=list(pack.get("boundary_tags") or []),
        refusal_reasons=reasons if refused else [],
    )
