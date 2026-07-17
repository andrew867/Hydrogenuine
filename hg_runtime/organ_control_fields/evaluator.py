"""OCF runtime — organ control fields evaluator."""

from __future__ import annotations

from typing import Any

from hg_core.governance.canonical_hash import canonical_hash
from hg_core.ocf.errors import (
    OCF_PANIC_DARK_RESTRICT,
    OCF_POSTURE_TRANSITION,
    REFUSED_AUTHORITY_CONVERSION,
    REFUSED_DURABLE_SINK,
    REFUSED_HIDE_PROOF_FAILURE,
    REFUSED_MEMORY_MUTATION,
    REFUSED_OEA_TER,
    REFUSED_PERMIT_MINT,
    REFUSED_PUBLISH,
    REFUSED_RECoupling_WITHOUT_AUDIT,
    REFUSED_SECRET_LEAK,
    REFUSED_SPAWN,
    REFUSED_SRP_APPLY,
    REFUSED_UEAK_APPROVAL,
    REFUSED_UNKNOWN_POSTURE,
)
from hg_core.ocf.no_authority import advisory_only_marker
from hg_core.ocf.types import (
    ControlFieldDuration,
    ControlFieldIntensity,
    ControlFieldReason,
    ControlFieldSidebandReceipt,
    ControlFieldSource,
    ControlFieldTarget,
    DecouplingPlan,
    OCFDecision,
    OrganControlField,
    OrganPostureState,
    PanicDarkReceipt,
    PostureTransition,
    PostureTransitionRefusal,
    ProbeRequest,
    ProbeResponse,
    RecouplingPlan,
    VALID_POSTURES,
)
from hg_core.secrets.redact import contains_leak

FIXTURE_CLOCK = "2026-06-14T01:00:00.000000Z"

_ADVERSARIAL_MAP: dict[str, str] = {
    "permit_mint": REFUSED_PERMIT_MINT,
    "ueak_approval": REFUSED_UEAK_APPROVAL,
    "oea_ter": REFUSED_OEA_TER,
    "srp_apply": REFUSED_SRP_APPLY,
    "memory_mutation": REFUSED_MEMORY_MUTATION,
    "spawn": REFUSED_SPAWN,
    "publish": REFUSED_PUBLISH,
    "durable_sink": REFUSED_DURABLE_SINK,
    "authority_conversion": REFUSED_AUTHORITY_CONVERSION,
    "hide_proof_failure": REFUSED_HIDE_PROOF_FAILURE,
}


def _field_from_fixture(data: dict[str, Any]) -> OrganControlField:
    posture = OrganPostureState(data.get("requested_posture", "DAMPED"))
    return OrganControlField(
        field_id=str(data.get("field_id", "ocf-field-fixture")),
        source=ControlFieldSource(str(data.get("source_id", "ocf-advisory"))),
        target=ControlFieldTarget(str(data.get("organ_id", "organ:fixture"))),
        intensity=ControlFieldIntensity(float(data.get("intensity", 0.5))),
        duration=ControlFieldDuration(until_observed_at=data.get("until", FIXTURE_CLOCK)),
        reason=ControlFieldReason(str(data.get("reason_code", "ocf.advisory.damp"))),
        requested_posture=posture,
        restrict_only=bool(data.get("restrict_only", True)),
    )


def apply_control_field(
    field: OrganControlField,
    *,
    current_posture: OrganPostureState,
    observed_at: str = FIXTURE_CLOCK,
) -> OCFDecision:
    """Apply advisory control field; never grants permission."""
    if field.requested_posture == OrganPostureState.UNKNOWN or field.requested_posture not in VALID_POSTURES:
        return OCFDecision(
            status="refused",
            reason_code=REFUSED_UNKNOWN_POSTURE,
            refusal=PostureTransitionRefusal(REFUSED_UNKNOWN_POSTURE, field.target.organ_id, field.requested_posture.value),
        )

    receipt = ControlFieldSidebandReceipt(
        receipt_id=f"ocf-sb-{canonical_hash({'field': field.field_id})[-12:]}",
        field_id=field.field_id,
        target_organ=field.target.organ_id,
        posture_from=current_posture.value,
        posture_to=field.requested_posture.value,
        observed_at=observed_at,
    )
    transition = PostureTransition(
        transition_id=f"ocf-tr-{field.field_id[-8:]}",
        organ_id=field.target.organ_id,
        from_posture=current_posture,
        to_posture=field.requested_posture,
        observed_at=observed_at,
        sideband_receipt=receipt,
    )
    reason = OCF_PANIC_DARK_RESTRICT if field.requested_posture == OrganPostureState.PANIC_DARK else OCF_POSTURE_TRANSITION
    return OCFDecision(
        status="recorded",
        reason_code=reason,
        transition=transition,
        sideband_receipt=receipt,
        extra={**advisory_only_marker()},
    )


def process_ocf_bundle(bundle: dict[str, Any], *, observed_at: str = FIXTURE_CLOCK) -> dict[str, Any]:
    signal = bundle.get("adversarial_signal")
    if signal and signal in _ADVERSARIAL_MAP:
        return {
            **advisory_only_marker(),
            "status": "refused",
            "bundle_id": bundle.get("bundle_id"),
            "reason_code": _ADVERSARIAL_MAP[signal],
            "adversarial_signal": signal,
        }

    if contains_leak(bundle):
        return {**advisory_only_marker(), "status": "refused", "reason_code": REFUSED_SECRET_LEAK, "bundle_id": bundle.get("bundle_id")}

    if bundle.get("action") == "recouple":
        if not bundle.get("audit_ref"):
            return {
                **advisory_only_marker(),
                "status": "refused",
                "reason_code": REFUSED_RECoupling_WITHOUT_AUDIT,
                "bundle_id": bundle.get("bundle_id"),
            }
        plan = RecouplingPlan(
            plan_id=str(bundle.get("plan_id", "recouple-1")),
            organ_id=str(bundle.get("organ_id", "organ:fixture")),
            audit_ref=str(bundle["audit_ref"]),
            observed_at=observed_at,
        )
        return {
            **advisory_only_marker(),
            "status": "recorded",
            "reason_code": OCF_POSTURE_TRANSITION,
            "recoupling_plan": plan.to_payload(),
            "bundle_id": bundle.get("bundle_id"),
        }

    if bundle.get("action") == "decouple":
        plan = DecouplingPlan(
            plan_id=str(bundle.get("plan_id", "decouple-1")),
            organ_id=str(bundle.get("organ_id", "organ:fixture")),
            buses_to_isolate=tuple(bundle.get("buses", ("bus:shared",))),
            observed_at=observed_at,
        )
        field = _field_from_fixture({**bundle, "requested_posture": "DECOUPLED"})
        decision = apply_control_field(field, current_posture=OrganPostureState.BRIGHT, observed_at=observed_at)
        result = decision.to_payload()
        result["decoupling_plan"] = plan.to_payload()
        result["bundle_id"] = bundle.get("bundle_id")
        return result

    if bundle.get("action") == "probe":
        req = ProbeRequest(
            request_id=str(bundle.get("request_id", "probe-1")),
            organ_id=str(bundle.get("organ_id", "organ:fixture")),
            diagnostic_kind=str(bundle.get("diagnostic_kind", "health")),
            observed_at=observed_at,
        )
        resp = ProbeResponse(req.request_id, req.organ_id, "ok", observed_at)
        field = _field_from_fixture({**bundle, "requested_posture": "PROBE_ONLY"})
        decision = apply_control_field(field, current_posture=OrganPostureState.BRIGHT, observed_at=observed_at)
        result = decision.to_payload()
        result["probe_request"] = req.to_payload()
        result["probe_response"] = resp.to_payload()
        result["bundle_id"] = bundle.get("bundle_id")
        return result

    if bundle.get("action") == "panic_dark":
        receipt = PanicDarkReceipt(
            receipt_id=f"ocf-panic-{bundle.get('organ_id', 'organ')[-6:]}",
            organ_id=str(bundle.get("organ_id", "organ:fixture")),
            observed_at=observed_at,
            restrict_only=True,
        )
        field = _field_from_fixture({**bundle, "requested_posture": "PANIC_DARK"})
        decision = apply_control_field(field, current_posture=OrganPostureState.BRIGHT, observed_at=observed_at)
        result = decision.to_payload()
        result["panic_dark_receipt"] = receipt.to_payload()
        result["bundle_id"] = bundle.get("bundle_id")
        return result

    field_data = bundle.get("control_field", bundle)
    current = OrganPostureState(bundle.get("current_posture", "BRIGHT"))
    field = _field_from_fixture(field_data)
    decision = apply_control_field(field, current_posture=current, observed_at=observed_at)
    result = decision.to_payload()
    result["bundle_id"] = bundle.get("bundle_id")
    return result


def replay_ocf_bundles(bundles: list[dict[str, Any]], *, observed_at: str = FIXTURE_CLOCK) -> str:
    hashes: list[str] = []
    for bundle in bundles:
        result = process_ocf_bundle(bundle, observed_at=observed_at)
        hashes.append(canonical_hash({k: result[k] for k in sorted(result) if k != "bundle_id"}))
    return canonical_hash({"hashes": hashes})


OCF_FIXTURE_BUNDLES: tuple[dict[str, Any], ...] = (
    {"bundle_id": "ocf-valid-damp", "control_field": {"field_id": "damp-1", "requested_posture": "DAMPED", "organ_id": "organ:h8"}},
    {"bundle_id": "ocf-valid-dark", "control_field": {"field_id": "dark-1", "requested_posture": "DARK", "organ_id": "organ:met"}},
    {"bundle_id": "ocf-valid-probe", "action": "probe", "organ_id": "organ:arm"},
    {"bundle_id": "ocf-valid-decouple", "action": "decouple", "organ_id": "organ:tep"},
    {"bundle_id": "ocf-valid-recouple", "action": "recouple", "organ_id": "organ:tep", "audit_ref": "audit:recouple-ok"},
    {"bundle_id": "ocf-panic-dark", "action": "panic_dark", "organ_id": "organ:bus"},
    {"bundle_id": "ocf-recouple-no-audit", "action": "recouple", "organ_id": "organ:tep"},
    {"bundle_id": "ocf-unknown-posture", "control_field": {"requested_posture": "UNKNOWN"}},
    {"bundle_id": "ocf-adversarial-permit", "adversarial_signal": "permit_mint"},
    {"bundle_id": "ocf-adversarial-ueak", "adversarial_signal": "ueak_approval"},
    {"bundle_id": "ocf-adversarial-oea", "adversarial_signal": "oea_ter"},
    {"bundle_id": "ocf-adversarial-srp", "adversarial_signal": "srp_apply"},
    {"bundle_id": "ocf-adversarial-mem", "adversarial_signal": "memory_mutation"},
    {"bundle_id": "ocf-adversarial-spawn", "adversarial_signal": "spawn"},
    {"bundle_id": "ocf-adversarial-publish", "adversarial_signal": "publish"},
    {"bundle_id": "ocf-adversarial-sink", "adversarial_signal": "durable_sink"},
    {"bundle_id": "ocf-adversarial-auth", "adversarial_signal": "authority_conversion"},
    {"bundle_id": "ocf-secret-leak", "control_field": {"api_key": "sk-abcdefghijklmnopqrstuvwxyz123456"}},
)


def load_ocf_fixtures() -> list[dict[str, Any]]:
    return list(OCF_FIXTURE_BUNDLES)


__all__ = [
    "FIXTURE_CLOCK",
    "apply_control_field",
    "load_ocf_fixtures",
    "process_ocf_bundle",
    "replay_ocf_bundles",
]
