"""CRT full service — snapshot, export, emit; certification evidence is not certification."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from hg_core.boundary_full.rtc_emit import emit_drafts, feature_enabled
from hg_core.policy_safety.config import crt_enabled, crt_include_exceptions
from hg_core.policy_safety.errors import (
    PolicyValidationError,
    REFUSED_EXCEPTION_SUPPRESSION,
    REFUSED_FAKE_GREEN,
)
from hg_runtime.certification_evidence_pack import rtc_bridge as bridge
from hg_runtime.certification_evidence_pack.export import (
    FIXTURE_CLOCK,
    build_auditor_export,
    build_snapshot_from_fixtures,
    export_advisory_payload,
)


def process_certification_export(
    *,
    snapshot_id: str,
    branch: str,
    head: str,
    claims: Sequence[Mapping[str, str]],
    exceptions: Sequence[Mapping[str, str]],
    evidence_refs: Sequence[Mapping[str, str]],
    bus: Any = None,
    observed_at: str = FIXTURE_CLOCK,
    suppress_exceptions: bool = False,
) -> dict[str, object]:
    """Full CRT pipeline: snapshot, honest export, optional RTC — no fake green."""
    if not crt_enabled() and not feature_enabled("HG_CRT_FORCE_EMIT", default="0"):
        return {
            "status": "disabled",
            "snapshot_id": snapshot_id,
            "permission_granted": False,
            "certification_granted": False,
            "crt_enabled": False,
        }

    if suppress_exceptions and crt_include_exceptions():
        drafts = [
            bridge.signal_refused(snapshot_id=snapshot_id, reason_code=REFUSED_EXCEPTION_SUPPRESSION),
        ]
        emitted = emit_drafts(bus, drafts, source="crt.service") if crt_enabled() else []
        return {
            "status": "refused",
            "snapshot_id": snapshot_id,
            "permission_granted": False,
            "certification_granted": False,
            "reason_code": REFUSED_EXCEPTION_SUPPRESSION,
            "draft_count": len(drafts),
            "emitted_count": len(emitted),
            "crt_enabled": crt_enabled(),
        }

    drafts: list[dict[str, Any]] = [
        bridge.certification_snapshot_requested(snapshot_id=snapshot_id, branch=branch, head=head),
    ]

    try:
        snapshot = build_snapshot_from_fixtures(
            snapshot_id=snapshot_id,
            branch=branch,
            head=head,
            claims=claims,
            exceptions=exceptions,
            evidence_refs=evidence_refs,
            created_at=observed_at,
        )
    except PolicyValidationError as exc:
        reason = str(exc.code)
        claim_id = "unknown"
        for claim in claims:
            if claim.get("status") == "supported" and not claim.get("evidence_refs"):
                claim_id = claim.get("claim_id", claim_id)
                break
        drafts.append(bridge.fake_green_prevented(claim_id=claim_id, reason_code=reason))
        drafts.append(bridge.signal_refused(snapshot_id=snapshot_id, reason_code=reason))
        emitted = emit_drafts(bus, drafts, source="crt.service") if crt_enabled() else []
        return {
            "status": "refused",
            "snapshot_id": snapshot_id,
            "permission_granted": False,
            "certification_granted": False,
            "reason_code": reason,
            "draft_count": len(drafts),
            "emitted_count": len(emitted),
            "crt_enabled": crt_enabled(),
        }

    for ref in snapshot.evidence_refs:
        drafts.append(
            bridge.evidence_reference_added(
                evidence_id=ref.evidence_id,
                path=ref.path,
                content_hash=ref.content_hash,
                fresh=ref.fresh,
            )
        )

    for claim in snapshot.claims:
        drafts.append(
            bridge.safety_claim_registered(
                claim_id=claim.claim_id,
                status=claim.status,
                record_hash=claim.record_hash,
            )
        )
        drafts.append(
            bridge.control_mapping_recorded(claim_id=claim.claim_id, control_domain=claim.control_domain)
        )
        if claim.status == "unsupported":
            drafts.append(
                bridge.unsupported_claim_detected(claim_id=claim.claim_id, statement=claim.statement)
            )
        if claim.status == "supported" and not claim.evidence_refs:
            drafts.append(
                bridge.fake_green_prevented(claim_id=claim.claim_id, reason_code=REFUSED_FAKE_GREEN)
            )

    for exc in snapshot.exceptions:
        drafts.append(
            bridge.exception_recorded(
                exception_id=exc.exception_id,
                control_domain=exc.control_domain,
                record_hash=exc.record_hash,
            )
        )

    bundle = build_auditor_export(snapshot)
    drafts.append(
        bridge.auditor_export_created(
            export_id=bundle.export_id,
            bundle_hash=bundle.bundle_hash,
            snapshot_id=snapshot.snapshot_id,
        )
    )

    emitted = emit_drafts(bus, drafts, source="crt.service") if crt_enabled() else []
    payload = export_advisory_payload(bundle)

    return {
        "status": "exported",
        "snapshot_id": snapshot_id,
        "permission_granted": False,
        "authority_created": False,
        "certification_granted": False,
        "snapshot": snapshot.to_payload(),
        "export": payload,
        "bundle_hash": bundle.bundle_hash,
        "exception_count": len(snapshot.exceptions),
        "draft_count": len(drafts),
        "emitted_count": len(emitted),
        "crt_enabled": crt_enabled(),
    }


__all__ = ["FIXTURE_CLOCK", "process_certification_export"]
