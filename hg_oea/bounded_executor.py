"""OEA bounded real executor — registered capabilities only."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Sequence

from hg_oea.binding import BindingError, binding_from_commit_payload, verify_binding_for_execution
from hg_oea.capabilities.local_report import execute_local_report_write
from hg_oea.compensation import compensate_local_report
from hg_oea.config import OEAConfig
from hg_oea.dry_run import perform_dry_run
from hg_oea.registry import lookup_capability
from hg_oea.receipts import OEAReceiptLedger
from hg_oea.retry import may_retry
from hg_oea import rtc_bridge
from hg_oea.types import EffectReceipt, OEABinding
from hg_oea.validation import ValidationError, redact_text
from hg_runtime.contract import Event, stable_id

from hg_core.admission.ingress import get_controller
from hg_core.admission.types import AdmissionRequest


class OEABoundedExecutor:
    """Executes registered bounded capabilities after UEAK commit — never stub fallback."""

    handler_id = "oea.bounded.executor"

    def __init__(self, config: OEAConfig | None = None, *, clock=None) -> None:
        self.config = config or OEAConfig.from_env()
        self._clock = clock or (lambda: "2026-06-12T00:00:00.000000Z")
        self.effect_records: List[Dict[str, Any]] = []
        self._ledger = OEAReceiptLedger(self.config.proof_dir / "receipts.jsonl")
        self.lockdown = self.config.lockdown

    @property
    def audit_records(self) -> List[Dict[str, Any]]:
        return self.effect_records

    def dispatch_committed(
        self, committed_events: Sequence[Event]
    ) -> List[Dict[str, Any]]:
        if not self.config.is_real:
            raise RuntimeError("OEABoundedExecutor requires HG_OEA_REAL=1 or HG_OEA_MODE=real")
        drafts: List[Dict[str, Any]] = []
        for committed in committed_events:
            if committed["type"] != "UEAK_EXECUTION_COMMITTED":
                continue
            parent = str(committed["event_id"])
            payload = committed.get("payload", {})
            drafts.extend(self._process_commit(payload, parent=parent))
        return drafts

    def _process_commit(self, payload: Mapping[str, Any], *, parent: str) -> List[Dict[str, Any]]:
        now = self._clock()
        capability_id = str(payload.get("capability_id") or "")
        drafts: List[Dict[str, Any]] = []
        try:
            dry_run_ref, dry_run_drafts = self._ensure_dry_run(payload, now=now, parent=parent)
            drafts.extend(dry_run_drafts)
            binding = binding_from_commit_payload(
                payload,
                created_at=now,
                config=self.config,
                dry_run_ref=dry_run_ref,
            )
            drafts.append(rtc_bridge.binding_created_draft(binding, parent=parent))
            verify_binding_for_execution(
                binding,
                arguments=binding.arguments,
                dry_run_hash=dry_run_ref,
            )
            drafts.append(rtc_bridge.execution_requested_draft(binding, parent=parent))
            drafts.append(rtc_bridge.execution_started_draft(binding, parent=parent))
            receipt = self._execute_binding(binding, now=now)
            drafts.append(rtc_bridge.execution_completed_draft(receipt, parent=parent))
            drafts.append(rtc_bridge.effect_receipt_recorded_draft(receipt, parent=parent))
            drafts.append(rtc_bridge.effect_receipted_draft(receipt, parent=parent))
            self.effect_records.append(receipt.to_payload())
        except BindingError as exc:
            refused_id = stable_id("oea_binding_refused", payload.get("commit_ref", ""))
            drafts.append(
                rtc_bridge.binding_refused_draft(
                    binding_id=refused_id,
                    capability_id=capability_id,
                    reason=exc.reason,
                    parent=parent,
                    ueak_commit_ref=str(payload.get("commit_ref", "")),
                )
            )
            drafts.append(
                rtc_bridge.execution_refused_draft(
                    binding_id=refused_id,
                    capability_id=capability_id,
                    reason=exc.reason,
                    parent=parent,
                )
            )
        except ValidationError as exc:
            drafts.append(
                rtc_bridge.execution_failed_draft(
                    binding_id=stable_id("oea_exec_failed", payload.get("commit_ref", "")),
                    capability_id=capability_id,
                    reason=exc.reason,
                    parent=parent,
                )
            )
        return drafts

    def _ensure_dry_run(
        self, payload: Mapping[str, Any], *, now: str, parent: str
    ) -> tuple[str, List[Dict[str, Any]]]:
        capability_id = str(payload.get("capability_id") or "")
        capability = lookup_capability(capability_id)
        if capability is None:
            raise BindingError("unknown_capability")
        if not capability.requires_dry_run:
            return "", []
        action = dict(payload.get("action", {}))
        existing = action.get("dry_run_ref")
        if existing:
            return str(existing), []
        binding = binding_from_commit_payload(
            payload,
            created_at=now,
            config=self.config,
            dry_run_ref=None,
            skip_dry_run_check=True,
        )
        drafts = [rtc_bridge.dry_run_started_draft(binding, parent=parent)]
        dry_run = perform_dry_run(binding, capability, config=self.config, created_at=now)
        drafts.append(rtc_bridge.dry_run_completed_draft(dry_run, parent=parent))
        if not dry_run.allowed:
            raise BindingError(dry_run.refusal_reason or "dry_run_refused")
        return dry_run.dry_run_hash, drafts

    def _execute_binding(self, binding: OEABinding, *, now: str) -> EffectReceipt:
        capability = lookup_capability(binding.capability_id)
        if capability is None:
            raise BindingError("unknown_capability")
        admission = get_controller().request(
            AdmissionRequest(
                request_id=binding.binding_id,
                kind="oea_effect",
                idempotency_key=f"oea:{binding.ueak_commit_ref}",
                capability_id=binding.capability_id,
                capability_concurrency=capability.max_concurrency,
            )
        )
        if not admission.admitted:
            raise BindingError(admission.reason_code)
        admission_token = admission.token
        try:
            retry_count = 0
            result_status = "failed"
            output_hash = ""
            touched: tuple[str, ...] = ()
            error_class: str | None = None
            error_message: str | None = None
            compensation_status = "none"
            while True:
                try:
                    if binding.capability_id == "local_report_file.write":
                        output_hash, touched = execute_local_report_write(
                            binding.arguments,
                            config=self.config,
                        )
                    else:
                        raise BindingError("unsupported_capability")
                    result_status = "executed"
                    break
                except ValidationError as exc:
                    error_class = "validation_error"
                    error_message = redact_text(exc.reason)
                    result_status = "failed"
                    if may_retry(capability, retry_count=retry_count, result_status=result_status):
                        retry_count += 1
                        continue
                    if capability.compensation_policy == "owned_path_cleanup":
                        compensation_status = compensate_local_report(
                            touched,
                            config=self.config,
                            capability=capability,
                        )
                        if compensation_status == "failed":
                            self.lockdown = True
                    break
            receipt = EffectReceipt(
                receipt_id=stable_id("oea_receipt", binding.binding_id, result_status),
                binding_id=binding.binding_id,
                capability_id=binding.capability_id,
                authority_ref=binding.authority_ref,
                ueak_commit_ref=binding.ueak_commit_ref,
                input_hash=binding.input_hash,
                result_status=result_status,  # type: ignore[arg-type]
                output_hash=output_hash,
                touched_resources=touched,
                started_at=now,
                completed_at=now,
                error_class=error_class,
                error_message_redacted=error_message,
                retry_count=retry_count,
                compensation_status=compensation_status,  # type: ignore[arg-type]
                executor_mode="real",
            )
            if result_status == "executed":
                get_controller().complete(admission_token, result_ref=receipt.receipt_id)
            return self._ledger.append(receipt)
        finally:
            get_controller().release(admission_token)


__all__ = ["OEABoundedExecutor"]
