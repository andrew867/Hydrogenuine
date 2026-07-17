"""CDO full service — classify, evaluate, route, emit."""

from __future__ import annotations

from typing import Any

from hg_core.boundary_full.rtc_emit import emit_drafts, feature_enabled
from hg_core.policy_safety.config import cdo_enabled
from hg_core.policy_safety.errors import PolicyValidationError, REFUSED_STALE_OPERATOR_SIGNAL
from hg_runtime.compromised_disconnected_operation import rtc_bridge as bridge
from hg_runtime.compromised_disconnected_operation.classifier import FIXTURE_CLOCK, classify_fixture
from hg_runtime.compromised_disconnected_operation.policy import (
    evaluate_posture,
    refuse_evidence_delete,
    refuse_widening_without_operator,
)
from hg_runtime.compromised_disconnected_operation.types import IsolationPosture, TrustSignal

_ROUTES: dict[IsolationPosture, tuple[str, ...]] = {
    "normal": ("PLT",),
    "suspect_network": ("DEP", "FTX", "PLT"),
    "suspect_credentials": ("SEC", "DEP", "FTX", "PLT"),
    "suspect_provider": ("DEP", "CRR", "FTX", "PLT"),
    "suspect_runtime": ("DEP", "SEC", "SAB", "PLT"),
    "operator_channel_absent": ("DEP", "ADM", "PLT"),
    "operator_channel_stale": ("DEP", "ADM", "PLT"),
    "fully_disconnected": ("DEP", "CRR", "ELS", "PLT"),
    "local_replay_only": ("DEP", "PLT", "TRL"),
    "safe_mode": ("DEP", "CRR", "PLT", "FTX"),
    "lockdown": ("DEP", "SEC", "CRR", "PLT", "FTX"),
    "unknown": ("DEP", "PLT", "SAB"),
}

_RECOVERY_POSTURES: frozenset[IsolationPosture] = frozenset(
    {"fully_disconnected", "lockdown", "safe_mode", "suspect_credentials", "suspect_provider"}
)


def route_advisory(posture: IsolationPosture, *, signal_id: str) -> dict[str, object]:
    targets = _ROUTES.get(posture, ("PLT", "operator_review"))
    return {
        "advisory_only": True,
        "permission_granted": False,
        "route_targets": list(targets),
        "signal_id": signal_id,
        "posture": posture,
        "routing_is_not_permission": True,
    }


def _append_posture_events(
    drafts: list[dict[str, Any]],
    *,
    signal_id: str,
    classified: IsolationPosture,
    effective: IsolationPosture,
    evaluation: dict[str, object],
) -> None:
    drafts.append(
        bridge.isolation_posture_selected(
            signal_id=signal_id,
            posture=effective,
            record_hash=str(evaluation.get("record_hash", "")),
        )
    )

    if effective in {"suspect_network", "fully_disconnected"}:
        drafts.append(bridge.network_suspected(signal_id=signal_id))
    if effective == "suspect_provider":
        drafts.append(bridge.provider_suspected(signal_id=signal_id))
    if effective == "operator_channel_stale":
        drafts.append(bridge.operator_channel_stale(signal_id=signal_id))
    if effective == "local_replay_only":
        drafts.append(bridge.local_replay_only_entered(signal_id=signal_id))
    if effective == "safe_mode" or classified == "unknown":
        drafts.append(bridge.safe_mode_recommended(signal_id=signal_id))
    if evaluation.get("evidence_preservation_recommended"):
        drafts.append(bridge.evidence_preservation_recommended(signal_id=signal_id, posture=effective))
    if effective in _RECOVERY_POSTURES:
        drafts.append(bridge.recovery_runbook_recommended(signal_id=signal_id, posture=effective))


def process_signal(
    signal: TrustSignal,
    *,
    text_hint: str = "",
    current_posture: IsolationPosture = "normal",
    operator_confirmed: bool = False,
    evidence_delete_requested: bool = False,
    bus: Any = None,
    observed_at: str = FIXTURE_CLOCK,
) -> dict[str, object]:
    """Full CDO pipeline: classify, evaluate, route, optional RTC emission."""
    if not cdo_enabled() and not feature_enabled("HG_CDO_FORCE_EMIT", default="0"):
        return {
            "status": "disabled",
            "signal_id": signal.signal_id,
            "permission_granted": False,
            "cdo_enabled": False,
        }

    drafts: list[dict[str, Any]] = []
    refused_reason: str | None = None

    try:
        refuse_evidence_delete(requested=evidence_delete_requested)
    except PolicyValidationError as exc:
        refused_reason = exc.reason_code
        drafts.append(bridge.signal_refused(signal_id=signal.signal_id, reason_code=exc.reason_code))

    classified = classify_fixture(signal, text_hint=text_hint)

    try:
        refuse_widening_without_operator(
            current=current_posture,
            proposed=classified,
            operator_confirmed=operator_confirmed,
        )
    except PolicyValidationError as exc:
        refused_reason = exc.reason_code
        drafts.append(bridge.signal_refused(signal_id=signal.signal_id, reason_code=exc.reason_code))

    evaluation = evaluate_posture(signal, classified)
    evaluation = {**evaluation, "record_hash": signal.record_hash}
    effective = str(evaluation["posture"])

    if signal.kind == "compromise":
        drafts.append(
            bridge.compromise_signal_received(
                signal_id=signal.signal_id,
                content_ref=signal.content_ref,
                record_hash=signal.record_hash,
            )
        )
    else:
        drafts.append(
            bridge.disconnection_signal_received(
                signal_id=signal.signal_id,
                content_ref=signal.content_ref,
                record_hash=signal.record_hash,
            )
        )

    if evaluation.get("reason_code") == REFUSED_STALE_OPERATOR_SIGNAL:
        drafts.append(bridge.operator_channel_stale(signal_id=signal.signal_id))
        drafts.append(
            bridge.signal_refused(
                signal_id=signal.signal_id,
                reason_code=REFUSED_STALE_OPERATOR_SIGNAL,
            )
        )

    _append_posture_events(
        drafts,
        signal_id=signal.signal_id,
        classified=classified,
        effective=effective,  # type: ignore[arg-type]
        evaluation=evaluation,
    )

    routing = route_advisory(effective, signal_id=signal.signal_id)  # type: ignore[arg-type]

    emitted = emit_drafts(bus, drafts, source="cdo.service") if cdo_enabled() else []

    return {
        "status": "recorded",
        "signal_id": signal.signal_id,
        "permission_granted": False,
        "authority_created": False,
        "classified_posture": classified,
        "evaluation": evaluation,
        "routing": routing,
        "refused_reason": refused_reason,
        "draft_count": len(drafts),
        "emitted_count": len(emitted),
        "cdo_enabled": cdo_enabled(),
        "observed_at": observed_at,
    }


__all__ = ["FIXTURE_CLOCK", "process_signal", "route_advisory"]
