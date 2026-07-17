"""OEA binding creation and validation."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Optional

from hg_core.capability_risk.enforce import (
    CatalogRefusal,
    lookup_catalog_entry,
    validate_binding_authorization,
)
from hg_oea.config import OEAConfig
from hg_oea.registry import is_capability_enabled, lookup_capability
from hg_oea.types import CapabilityDefinition, OEABinding
from hg_oea.validation import ValidationError, argument_schema_hash, input_hash, validate_arguments
from hg_runtime.contract import stable_id


class BindingError(Exception):
    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


def create_binding(
    *,
    capability_id: str,
    ueak_commit_ref: str,
    authority_ref: str,
    requested_by: str,
    arguments: Mapping[str, Any],
    created_at: str,
    config: OEAConfig,
    gpp_permit_ref: str | None = None,
    hal_or_soar_ref: str | None = None,
    confirmation_ref: str | None = None,
    dry_run_ref: str | None = None,
    expires_at: str | None = None,
    skip_dry_run_check: bool = False,
    review_metadata: Mapping[str, Any] | None = None,
) -> OEABinding:
    if config.lockdown:
        raise BindingError("oea_lockdown")
    catalog_entry = lookup_catalog_entry(capability_id)
    if catalog_entry is None:
        raise BindingError("uncataloged_capability")
    try:
        validate_binding_authorization(
            catalog_entry,
            config=config,
            review_metadata=review_metadata,
        )
    except CatalogRefusal as exc:
        short = exc.reason.rsplit(".", 1)[-1]
        if short == "uncataloged":
            short = "uncataloged_capability"
        elif short == "disabled":
            short = "capability_disabled"
        raise BindingError(short) from exc
    capability = lookup_capability(capability_id)
    if capability is None:
        raise BindingError("unknown_capability")
    if capability.risk_class == "prohibited":
        raise BindingError("capability_prohibited")
    if not is_capability_enabled(capability_id, config.allowed_capabilities):
        raise BindingError("capability_disabled")
    if not ueak_commit_ref:
        raise BindingError("missing_ueak_commit_ref")
    if "ueak_commit_ref" in capability.authority_requirements and not ueak_commit_ref:
        raise BindingError("missing_ueak_commit_ref")
    if "confirmation_ref" in capability.authority_requirements and not confirmation_ref:
        raise BindingError("missing_confirmation_ref")
    if capability.requires_human_confirmation and not confirmation_ref:
        if capability.risk_class in {"medium", "high"} and config.require_confirmation_for_medium:
            raise BindingError("confirmation_required")
    if capability.requires_dry_run and not dry_run_ref and not skip_dry_run_check:
        raise BindingError("dry_run_required")
    try:
        validated = validate_arguments(capability, arguments)
    except ValidationError as exc:
        raise BindingError(exc.reason) from exc
    computed_hash = input_hash(validated)
    binding_id = stable_id("oea_binding", ueak_commit_ref, capability_id, computed_hash)
    return OEABinding(
        binding_id=binding_id,
        created_at=created_at,
        capability_id=capability_id,
        authority_ref=authority_ref,
        ueak_commit_ref=ueak_commit_ref,
        gpp_permit_ref=gpp_permit_ref,
        hal_or_soar_ref=hal_or_soar_ref,
        requested_by=requested_by,
        input_hash=computed_hash,
        argument_schema_hash=argument_schema_hash(capability),
        risk_class=capability.risk_class,
        confirmation_ref=confirmation_ref,
        dry_run_ref=dry_run_ref,
        expires_at=expires_at,
        status="created",
        arguments=validated,
    )


def verify_binding_for_execution(
    binding: OEABinding,
    *,
    arguments: Mapping[str, Any],
    dry_run_hash: str | None = None,
) -> None:
    if binding.status in {"executing", "executed", "closed"}:
        raise BindingError("binding_immutable")
    computed = input_hash(arguments)
    if computed != binding.input_hash:
        raise BindingError("input_hash_mismatch")
    capability = lookup_capability(binding.capability_id)
    if capability is None:
        raise BindingError("unknown_capability")
    if capability.requires_dry_run:
        if not binding.dry_run_ref:
            raise BindingError("dry_run_required")
        if dry_run_hash and dry_run_hash != binding.dry_run_ref:
            raise BindingError("dry_run_hash_mismatch")


def binding_from_commit_payload(
    payload: Mapping[str, Any],
    *,
    created_at: str,
    config: OEAConfig,
    dry_run_ref: str | None = None,
    skip_dry_run_check: bool = False,
    review_metadata: Mapping[str, Any] | None = None,
) -> OEABinding:
    action = dict(payload.get("action", {}))
    capability_id = str(
        payload.get("capability_id")
        or action.get("capability_id")
        or ""
    )
    arguments = dict(action.get("arguments") or action.get("args") or {})
    return create_binding(
        capability_id=capability_id,
        ueak_commit_ref=str(payload.get("commit_ref", "")),
        authority_ref=str(payload.get("decision_id") or payload.get("request_id", "")),
        requested_by=str(payload.get("requested_by") or "ueak"),
        arguments=arguments,
        created_at=created_at,
        config=config,
        gpp_permit_ref=str(payload.get("permit_ref")) if payload.get("permit_ref") else None,
        hal_or_soar_ref=str(action.get("hal_or_soar_ref")) if action.get("hal_or_soar_ref") else None,
        confirmation_ref=str(action.get("confirmation_ref")) if action.get("confirmation_ref") else None,
        dry_run_ref=str(dry_run_ref or action.get("dry_run_ref") or "") or None,
        skip_dry_run_check=skip_dry_run_check,
        review_metadata=review_metadata
        or dict(payload.get("review_metadata") or action.get("review_metadata") or {}),
    )


__all__ = [
    "BindingError",
    "binding_from_commit_payload",
    "create_binding",
    "verify_binding_for_execution",
]
