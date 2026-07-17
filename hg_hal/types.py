"""HAL Phase 1 arbitration models — route only, no permits or execution."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Mapping

from hg_core.governance.canonical_hash import canonical_hash

ArbitrationRouting = Literal["ACCEPT", "REJECT", "DEFER", "NO_OP"]

ARBITRATION_SCHEMA = "hal-arbitration-request"
ARBITRATION_RESULT_SCHEMA = "hal-arbitration-result"
ARBITRATION_SCHEMA_VERSION = "1.0"


@dataclass(frozen=True)
class ArbitrationCandidate:
    """A decision candidate action reference (not an executable handle)."""

    candidate_id: str
    action_ref: str
    capability_id: str
    effect_class: str
    priority: int = 0

    def to_payload(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "action_ref": self.action_ref,
            "capability_id": self.capability_id,
            "effect_class": self.effect_class,
            "priority": self.priority,
        }


@dataclass(frozen=True)
class ArbitrationRequest:
    """HAL arbitration input — proposal and candidate refs only."""

    request_id: str
    proposal_ref: str
    candidates: tuple[ArbitrationCandidate, ...]
    context_refs: tuple[str, ...]
    aep_modulation_refs: tuple[str, ...] = ()
    aep_max_severity: int = 0
    scrutiny_depth_delta: int = 0
    soar_run_ref: str | None = None
    soar_binding: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema": ARBITRATION_SCHEMA,
            "schema_version": ARBITRATION_SCHEMA_VERSION,
            "request_id": self.request_id,
            "proposal_ref": self.proposal_ref,
            "candidate_refs": [candidate.action_ref for candidate in self.candidates],
            "candidates": [candidate.to_payload() for candidate in self.candidates],
            "context_refs": list(self.context_refs),
            "aep_modulation_refs": list(self.aep_modulation_refs),
            "aep_max_severity": self.aep_max_severity,
            "scrutiny_depth_delta": self.scrutiny_depth_delta,
            "soar_run_ref": self.soar_run_ref,
            "soar_binding": self.soar_binding,
        }


@dataclass(frozen=True)
class ArbitrationResult:
    """HAL routing outcome — no permit fields."""

    request_id: str
    routing: ArbitrationRouting
    selected_candidate_ref: str | None
    reason_code: str
    trace_refs: tuple[str, ...]
    deferred_candidate_refs: tuple[str, ...] = ()

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload = {
            "schema": ARBITRATION_RESULT_SCHEMA,
            "schema_version": ARBITRATION_SCHEMA_VERSION,
            "request_id": self.request_id,
            "routing": self.routing,
            "selected_candidate_ref": self.selected_candidate_ref,
            "reason_code": self.reason_code,
            "trace_refs": list(self.trace_refs),
            "deferred_candidate_refs": list(self.deferred_candidate_refs),
        }
        if include_hash:
            payload["arbitration_hash"] = canonical_hash(payload)
        return payload


def request_from_proposal(
    proposal: Mapping[str, Any],
    *,
    context_refs: tuple[str, ...],
    aep_state: Mapping[str, Any],
    aep_modulation_refs: tuple[str, ...] = (),
    soar_run: Any | None = None,
) -> ArbitrationRequest:
    """Build an arbitration request from a cognition proposal event."""
    from hg_runtime.contract import stable_id

    payload = proposal.get("payload", {})
    proposal_id = str(payload.get("proposal_id") or proposal.get("event_id"))
    content = dict(payload.get("content", {}))
    capability_id = str(content.get("capability_id") or "cap.oea_stub_log")
    effect_class = str(content.get("effect_class") or "audit_log")
    action_type = str(content.get("action_type") or "oea_stub_log")
    candidate = ArbitrationCandidate(
        candidate_id=stable_id("hal_cand", proposal_id),
        action_ref=stable_id("hal_action", proposal_id, action_type),
        capability_id=capability_id,
        effect_class=effect_class,
        priority=int(content.get("priority", 0)),
    )
    scrutiny = 0
    if aep_modulation_refs:
        scrutiny = max(scrutiny, len(aep_modulation_refs))
    return ArbitrationRequest(
        request_id=stable_id("hal_req", proposal_id),
        proposal_ref=proposal_id,
        candidates=(candidate,),
        context_refs=context_refs,
        aep_modulation_refs=aep_modulation_refs,
        aep_max_severity=int(aep_state.get("max_severity", 0)),
        scrutiny_depth_delta=scrutiny,
        soar_run_ref=getattr(soar_run, "request_id", None),
        soar_binding=getattr(soar_run, "binding", None),
    )


__all__ = [
    "ARBITRATION_RESULT_SCHEMA",
    "ARBITRATION_SCHEMA",
    "ARBITRATION_SCHEMA_VERSION",
    "ArbitrationCandidate",
    "ArbitrationRequest",
    "ArbitrationResult",
    "ArbitrationRouting",
    "request_from_proposal",
]
