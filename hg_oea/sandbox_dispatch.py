"""Slice 2 bounded dispatch — fake-sink / sandbox dispatch with single-use permits.

This is the "live dispatch wiring" of UEAK/OEA Slice 2 in its honest sense: a REAL
code path through the dispatcher and receipt system, bounded to a fake in-memory
sink or a sandbox directory the caller controls. It is NOT real external dispatch:
no network access, no live posting, no writes outside the caller-supplied sandbox,
no child processes. Real external dispatch stays behind the default-off
`HG_OEA_REAL`/`HG_OEA_MODE=real` flags, which this module never reads and refuses
to honor (`config.is_real` is rejected outright).

Boundary order (documented choice): preflight (handoff hash, mode, capability,
config) → permit consume (lock-guarded, exactly once) → bounded effect → receipts.
A failed preflight never consumes the permit. A post-consume effect failure leaves
the permit consumed plus a failed dispatch receipt — deterministic and fail-safe:
an effect that may have been attempted can never be replayed.

Every outcome — dispatched, refused, failed — appends a chained EffectReceipt with
`external_effect_performed: False` inside the hashed payload. Receipts here use
executor_mode "fake_sink" or "sandboxed", never "real", so `is_live_effect_evidence`
can never promote them to live-effect evidence.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping, Optional

from hg_core.governance.canonical_hash import canonical_hash
from hg_gpp import PermitAuthority
from hg_gpp.models import fixture_permit_request
from hg_gpp.store import ConsumeResult, PermitConsumeReceipt, PermitStore
from hg_oea.capabilities.local_report import execute_local_report_write
from hg_oea.config import OEAConfig
from hg_oea.receipts import OEAReceiptLedger
from hg_oea.registry import is_capability_enabled, lookup_capability
from hg_oea.ter_handoff import TERHandoff, TERHandoffError, create_ter_handoff
from hg_oea.types import EffectReceipt
from hg_oea.validation import ValidationError
from hg_ueak import (
    ExecutionAuthorityKernel, RollbackRequirement, fixture_execution_request,
)

SANDBOX_CAPABILITY = "local_report_file.write"
_MODE_EXECUTOR = {"fake_sink": "fake_sink", "sandbox": "sandboxed"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


@dataclass
class Slice2DispatchOutcome:
    dispatched: bool
    reason: str
    dispatch_receipt: EffectReceipt | None
    consume_receipt: PermitConsumeReceipt | None
    consume_result: ConsumeResult | None


def execute_slice2_dispatch(
    handoff: TERHandoff,
    *,
    arguments: Mapping[str, Any],
    ledger: OEAReceiptLedger,
    permit_store: PermitStore,
    config: OEAConfig,
) -> Slice2DispatchOutcome:
    """Dispatch a TER handoff to a bounded sink; consume the permit exactly once."""
    created_at = _now()
    dispatch_id = f"slice2-dispatch-{handoff.record_hash[7:19]}"

    def _refusal(code: str, *, mode: str) -> Slice2DispatchOutcome:
        receipt = ledger.append(_receipt(
            handoff, dispatch_id=dispatch_id, executor_mode=mode,
            result_status="refused", output_hash="", touched=(),
            error_class=code, created_at=created_at))
        return Slice2DispatchOutcome(False, code, receipt, None, None)

    executor_mode = _MODE_EXECUTOR.get(handoff.dispatch_mode, "blocked")

    # ---- Preflight: nothing below consumes the permit ----
    if not handoff.verify_hash():
        return _refusal("handoff_hash_invalid", mode=executor_mode)
    if handoff.dispatch_mode not in _MODE_EXECUTOR:
        return _refusal("unsupported_dispatch_mode", mode="blocked")
    if not handoff.translation.allowed:
        return _refusal("translation_refused", mode=executor_mode)
    if config.is_real:
        return _refusal("real_mode_not_permitted_in_slice2", mode=executor_mode)
    capability = lookup_capability(handoff.capability_id)
    if capability is None:
        return _refusal("unknown_capability", mode=executor_mode)
    allowed = config.allowed_capabilities or frozenset({SANDBOX_CAPABILITY})
    if handoff.dispatch_mode == "sandbox":
        if handoff.capability_id != SANDBOX_CAPABILITY:
            return _refusal("unsupported_sink", mode=executor_mode)
        if not is_capability_enabled(handoff.capability_id, allowed):
            return _refusal("capability_not_enabled", mode=executor_mode)

    # ---- Consume the permit (exactly once) ----
    consume = permit_store.consume(
        handoff.permit_id, now=created_at, consumed_by=dispatch_id,
        handoff_ref=handoff.handoff_id)
    if not consume.ok:
        receipt = ledger.append(_receipt(
            handoff, dispatch_id=dispatch_id, executor_mode=executor_mode,
            result_status="refused", output_hash="", touched=(),
            error_class=f"permit_{consume.reason}", created_at=created_at))
        return Slice2DispatchOutcome(False, f"permit_{consume.reason}",
                                     receipt, None, consume)

    # ---- Bounded effect (permit is now consumed either way) ----
    if handoff.dispatch_mode == "fake_sink":
        # In-memory sink only: the "output" is the hashed handoff record itself.
        output_hash = canonical_hash({"fake_sink_record": handoff.to_payload()})
        touched: tuple[str, ...] = ()
        status, error_class = "executed", None
    else:
        try:
            output_hash, touched = execute_local_report_write(arguments, config=config)
            status, error_class = "executed", None
        except ValidationError as exc:
            output_hash, touched = "", ()
            status, error_class = "failed", f"sandbox_write_failed:{exc}"

    receipt = ledger.append(_receipt(
        handoff, dispatch_id=dispatch_id, executor_mode=executor_mode,
        result_status=status, output_hash=output_hash, touched=touched,
        error_class=error_class, created_at=created_at))
    return Slice2DispatchOutcome(status == "executed",
                                 status if error_class is None else error_class,
                                 receipt, consume.receipt, consume)


def _receipt(handoff: TERHandoff, *, dispatch_id: str, executor_mode: str,
             result_status: str, output_hash: str, touched: tuple[str, ...],
             error_class: str | None, created_at: str) -> EffectReceipt:
    return EffectReceipt(
        receipt_id=dispatch_id,
        binding_id=handoff.handoff_id,
        capability_id=handoff.capability_id,
        authority_ref=handoff.ueak_receipt_hash,
        ueak_commit_ref=handoff.ueak_receipt_hash,
        input_hash=handoff.input_hash,
        result_status=result_status,  # type: ignore[arg-type]
        output_hash=output_hash,
        touched_resources=touched,
        started_at=created_at,
        completed_at=_now(),
        error_class=error_class,
        executor_mode=executor_mode,
        permit_id=handoff.permit_id,
        handoff_id=handoff.handoff_id,
        sink_type=handoff.sink_type,
        dispatch_mode=handoff.dispatch_mode,
        external_effect_performed=False,
    )


@dataclass
class Slice2RunArtifacts:
    permit: Any
    admission_receipt: Any
    dispatch_plan: Any
    handoff: TERHandoff | None
    outcome: Slice2DispatchOutcome | None
    permit_store: PermitStore
    kernel: ExecutionAuthorityKernel
    refusal: str | None = None


def run_slice2_boundary(
    *,
    capability_id: str = SANDBOX_CAPABILITY,
    proposed_action: Mapping[str, Any],
    ledger: OEAReceiptLedger,
    config: OEAConfig,
    dispatch_mode: str = "sandbox",
    sink_type: str = "sandbox_file",
    authority: Optional[PermitAuthority] = None,
) -> Slice2RunArtifacts:
    """Full bounded path: permit → UEAK admit → handoff → dispatch → consume."""
    authority = authority or PermitAuthority(permit_ttl_s=300.0)
    input_hash = canonical_hash(dict(proposed_action))
    cap = lookup_capability(capability_id)
    permit_decision = authority.issue(fixture_permit_request(
        request_id=f"slice2-permit-{input_hash[7:19]}",
        capability_ref=capability_id,
        effect_class=cap.effect_type if cap else "audit_log"))
    permit = permit_decision.permit
    kernel = ExecutionAuthorityKernel(permit_store=authority.store)
    request = fixture_execution_request(
        permit, rollback=RollbackRequirement(required=False))
    decision = kernel.admit(request)
    receipt = getattr(decision, "receipt", None)
    plan = getattr(decision, "dispatch_plan", None)
    try:
        handoff = create_ter_handoff(
            admission_receipt=receipt, dispatch_plan=plan,
            proposed_action=proposed_action, dispatch_mode=dispatch_mode,
            sink_type=sink_type, created_at=_now())
    except TERHandoffError as exc:
        return Slice2RunArtifacts(permit, receipt, plan, None, None,
                                  authority.store, kernel, refusal=exc.code)
    outcome = execute_slice2_dispatch(
        handoff, arguments=proposed_action, ledger=ledger,
        permit_store=authority.store, config=config)
    return Slice2RunArtifacts(permit, receipt, plan, handoff, outcome,
                              authority.store, kernel)


def validate_slice2_chain(artifacts: Slice2RunArtifacts,
                          ledger: OEAReceiptLedger) -> dict[str, Any]:
    """Cross-link validation: request → permit → admission → handoff → dispatch → consume."""
    failures: list[str] = []
    permit, receipt = artifacts.permit, artifacts.admission_receipt
    handoff, outcome = artifacts.handoff, artifacts.outcome
    if handoff is None or outcome is None or outcome.dispatch_receipt is None:
        return {"ok": False, "failures": ["incomplete_artifacts"]}
    dispatch = outcome.dispatch_receipt
    consume = outcome.consume_receipt
    if getattr(receipt, "status", "") != "admitted":
        failures.append("admission_not_admitted")
    if handoff.ueak_receipt_hash != getattr(receipt, "receipt_hash", ""):
        failures.append("handoff_admission_link_broken")
    if handoff.request_id != getattr(receipt, "request_id", ""):
        failures.append("handoff_request_link_broken")
    if not (permit.permit_id == getattr(receipt, "permit_id", "")
            == handoff.permit_id == dispatch.permit_id):
        failures.append("permit_id_link_broken")
    if handoff.permit_hash != permit.permit_hash:
        failures.append("permit_hash_link_broken")
    if dispatch.handoff_id != handoff.handoff_id:
        failures.append("dispatch_handoff_link_broken")
    if not handoff.verify_hash():
        failures.append("handoff_hash_invalid")
    if consume is not None:
        if consume.permit_id != permit.permit_id or consume.permit_hash != permit.permit_hash:
            failures.append("consume_permit_link_broken")
        if consume.consumed_by != dispatch.receipt_id:
            failures.append("consume_dispatch_link_broken")
        if consume.handoff_ref != handoff.handoff_id:
            failures.append("consume_handoff_link_broken")
    elif dispatch.result_status == "executed":
        failures.append("missing_consume_receipt")
    chain = ledger.verify_chain()
    if not chain.get("ok"):
        failures.append(f"ledger_chain_invalid:{chain.get('error')}")
    return {"ok": not failures, "failures": failures,
            "ledger_entries": chain.get("count", 0)}


__all__ = [
    "SANDBOX_CAPABILITY",
    "Slice2DispatchOutcome",
    "Slice2RunArtifacts",
    "execute_slice2_dispatch",
    "run_slice2_boundary",
    "validate_slice2_chain",
]
