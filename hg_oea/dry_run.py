"""OEA dry-run / simulation for bounded capabilities."""

from __future__ import annotations

from pathlib import Path
from typing import Mapping

from hg_core.time.expiry import validate_dry_run_window
from hg_oea.config import OEAConfig
from hg_oea.types import CapabilityDefinition, DryRunResult, OEABinding
from hg_oea.validation import ValidationError, canonical_hash, resolve_proof_path
from hg_runtime.contract import stable_id


class DryRunError(Exception):
    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


def perform_dry_run(
    binding: OEABinding,
    capability: CapabilityDefinition,
    *,
    config: OEAConfig,
    created_at: str,
) -> DryRunResult:
    if capability.capability_id == "local_report_file.write":
        return _dry_run_local_report(binding, capability, config=config, created_at=created_at)
    return DryRunResult(
        dry_run_id=stable_id("oea_dry_run", binding.binding_id),
        capability_id=capability.capability_id,
        input_hash=binding.input_hash,
        predicted_effect="unsupported_capability",
        touched_resources=(),
        risk_class=capability.risk_class,
        allowed=False,
        refusal_reason="unsupported_capability",
        dry_run_hash="",
    )


def _dry_run_local_report(
    binding: OEABinding,
    capability: CapabilityDefinition,
    *,
    config: OEAConfig,
    created_at: str,
) -> DryRunResult:
    args = dict(binding.arguments)
    filename = str(args.get("filename", ""))
    overwrite = bool(args.get("overwrite", False))
    try:
        target = resolve_proof_path(config.proof_dir, filename)
    except ValidationError as exc:
        return _refused_dry_run(binding, capability, reason=exc.reason)
    if target.exists() and not overwrite:
        return _refused_dry_run(binding, capability, reason="file_exists_without_overwrite")
    touched = (str(target),)
    payload = {
        "capability_id": capability.capability_id,
        "input_hash": binding.input_hash,
        "predicted_effect": "write_local_report_file",
        "touched_resources": list(touched),
        "created_at": created_at,
    }
    dry_run_hash = canonical_hash(payload)
    return DryRunResult(
        dry_run_id=stable_id("oea_dry_run", binding.binding_id, dry_run_hash),
        capability_id=capability.capability_id,
        input_hash=binding.input_hash,
        predicted_effect="write_local_report_file",
        touched_resources=touched,
        risk_class=capability.risk_class,
        allowed=True,
        dry_run_hash=dry_run_hash,
    )


def _refused_dry_run(
    binding: OEABinding,
    capability: CapabilityDefinition,
    *,
    reason: str,
) -> DryRunResult:
    return DryRunResult(
        dry_run_id=stable_id("oea_dry_run", binding.binding_id, "refused"),
        capability_id=capability.capability_id,
        input_hash=binding.input_hash,
        predicted_effect="refused",
        touched_resources=(),
        risk_class=capability.risk_class,
        allowed=False,
        refusal_reason=reason,
        dry_run_hash="",
    )


def is_dry_run_stale(
    dry_run: DryRunResult,
    *,
    created_at: str,
    ttl_seconds: float,
    current_input_hash: str | None = None,
    now: str | None = None,
) -> bool:
    stamp = dry_run.created_at or created_at
    ok, _reason = validate_dry_run_window(
        dry_run_created_at=stamp,
        dry_run_input_hash=dry_run.input_hash,
        current_input_hash=current_input_hash or dry_run.input_hash,
        now=now or stamp,
        ttl_seconds=ttl_seconds,
    )
    return not ok


__all__ = ["DryRunError", "is_dry_run_stale", "perform_dry_run"]
