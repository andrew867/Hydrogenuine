"""Dry-run executor — receipted terminal-effect requests with NO external effect.

Morning hardening tranche (2026-07-03): composes the machinery that already exists —
UEAK admission (fake dispatch sink), the OEA capability catalog, and
`perform_dry_run` — into a standalone receipted path:

    request → UEAK admit (fake sink) → capability lookup → dry-run simulation → STOP
    → chained dry-run EffectReceipt (executor_mode="dry_run", dry_run flag inside the
      hashed payload)

Un-promotability: `is_live_effect_evidence()` is the single arbiter — a dry-run
receipt can NEVER satisfy a live-effect evidence requirement, and stripping the
dry-run marker breaks the ledger's hash chain.

This module performs no filesystem writes outside the receipt ledger, no network
access, and spawns no child processes. UEAK/OEA Slice 2 (2026-07-03) added the TER
handoff, bounded fake-sink/sandbox dispatch, and single-use permit consume in
`ter_handoff.py` / `sandbox_dispatch.py`; real external dispatch remains disabled
by default and nothing here claims live execution.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from hg_oea.dry_run import perform_dry_run
from hg_oea.receipts import OEAReceiptLedger
from hg_oea.registry import lookup_capability
from hg_oea.config import OEAConfig
from hg_oea.types import EffectReceipt, OEABinding
from hg_core.policy_safety.hashing import canonical_hash
from hg_gpp import PermitAuthority
from hg_gpp.models import fixture_permit_request
from hg_ueak import (
    ExecutionAuthorityKernel, RollbackRequirement, fixture_execution_request,
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


@dataclass
class DryRunOutcome:
    admitted: bool
    admission_reason: str
    receipt: EffectReceipt | None
    dry_run_allowed: bool
    predicted_effect: str


def execute_dry_run(
    *,
    capability_id: str,
    proposed_action: Mapping[str, Any],
    ledger: OEAReceiptLedger,
    kernel: ExecutionAuthorityKernel | None = None,
    config: OEAConfig | None = None,
    requested_by: str = "dry_run_executor",
    authority_ref: str = "dryrun-authority-demo",
) -> DryRunOutcome:
    """Run the full boundary path in dry-run mode; never performs an effect."""
    created_at = _now()
    input_hash = canonical_hash(dict(proposed_action))

    # Real GPP permit + real UEAK admission — dispatched only to the fake sink.
    if kernel is None:
        authority = PermitAuthority(permit_ttl_s=300.0)
        permit_decision = authority.issue(
            fixture_permit_request(request_id=f"dryrun-permit-{input_hash[7:19]}"))
        kernel = ExecutionAuthorityKernel(permit_store=authority.store)
        request = fixture_execution_request(
            permit_decision.permit, rollback=RollbackRequirement(required=False))
    else:
        request = fixture_execution_request(
            None, rollback=RollbackRequirement(required=False))
    decision = kernel.admit(request)
    admitted = getattr(decision, "status", "") == "admitted"
    admission_reason = ("admitted_to_fake_sink" if admitted else
                        "; ".join(str(getattr(r, "code", r))
                                  for r in getattr(decision, "refusal_reasons", [])) or "refused")
    ueak_receipt = getattr(decision, "receipt", None)
    ueak_ref = getattr(ueak_receipt, "receipt_hash", "") or "ueak-fake-sink"

    capability = lookup_capability(capability_id)
    if capability is None:
        receipt = _dry_run_receipt(
            capability_id=capability_id, authority_ref=authority_ref,
            ueak_commit_ref=ueak_ref,
            input_hash=input_hash, created_at=created_at,
            predicted_effect="unknown_capability", refusal="unknown_capability")
        receipt = ledger.append(receipt)
        return DryRunOutcome(admitted, admission_reason, receipt, False, "unknown_capability")

    binding = OEABinding(
        binding_id=f"dryrun-bind-{input_hash[7:19]}",
        created_at=created_at,
        capability_id=capability_id,
        authority_ref=authority_ref,
        ueak_commit_ref=ueak_ref,
        gpp_permit_ref=None,
        hal_or_soar_ref=None,
        requested_by=requested_by,
        input_hash=input_hash,
        argument_schema_hash=canonical_hash({"schema": capability_id}),
        risk_class=capability.risk_class,
        arguments=dict(proposed_action),
    )
    result = perform_dry_run(binding, capability,
                             config=config or OEAConfig(), created_at=created_at)

    receipt = _dry_run_receipt(
        capability_id=capability_id, authority_ref=authority_ref,
        ueak_commit_ref=binding.ueak_commit_ref, input_hash=input_hash,
        created_at=created_at, predicted_effect=result.predicted_effect,
        refusal=result.refusal_reason if not result.allowed else None,
        dry_run_hash=result.dry_run_hash,
        touched=tuple(result.touched_resources))
    receipt = ledger.append(receipt)
    return DryRunOutcome(admitted, admission_reason, receipt, result.allowed,
                         result.predicted_effect)


def _dry_run_receipt(*, capability_id: str, authority_ref: str, ueak_commit_ref: str,
                     input_hash: str, created_at: str, predicted_effect: str,
                     refusal: str | None = None, dry_run_hash: str = "",
                     touched: tuple[str, ...] = ()) -> EffectReceipt:
    return EffectReceipt(
        receipt_id=f"dryrun-rcpt-{input_hash[7:19]}",
        binding_id=f"dryrun-bind-{input_hash[7:19]}",
        capability_id=capability_id,
        authority_ref=authority_ref,
        ueak_commit_ref=ueak_commit_ref,
        input_hash=input_hash,
        # dry runs are never "executed"; output stays empty — no effect happened
        result_status="dry_run_required",
        output_hash="",
        touched_resources=touched,
        started_at=created_at,
        completed_at=_now(),
        error_class=None if refusal is None else "dry_run_refused",
        error_message_redacted=refusal,
        executor_mode="dry_run",
    )


def is_live_effect_evidence(receipt_payload: Mapping[str, Any]) -> bool:
    """The single arbiter for live-effect claims. Dry-run receipts NEVER qualify."""
    return (
        receipt_payload.get("executor_mode") == "real"
        and receipt_payload.get("result_status") == "executed"
        and bool(receipt_payload.get("output_hash"))
        and receipt_payload.get("error_class") is None
        # Slice 2: fake_sink/sandboxed receipts carry an explicit False marker
        # inside the hashed payload; an explicit False can never be live evidence.
        and receipt_payload.get("external_effect_performed") is not False
    )


def snapshot_tree(root: Path) -> dict[str, str]:
    """Filesystem evidence helper: relative-path -> sha256 for no-effect proofs."""
    import hashlib
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob("*")) if p.is_file()}


__all__ = ["execute_dry_run", "is_live_effect_evidence", "snapshot_tree", "DryRunOutcome"]
