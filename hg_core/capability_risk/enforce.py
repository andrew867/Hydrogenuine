"""Read-only capability risk enforcement helpers (CT-12 CAP).

This module classifies and refuses; it never grants OEA authority or enables capabilities.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Mapping

from hg_core.capability_risk.catalog import (
    HIGH_REVIEW_RISK_CLASSES,
    CapabilityCatalog,
    CatalogEntry,
    default_catalog_path,
    load_catalog,
    tier_meets,
)

REASON_UNCATALOGED = "capability.refused.uncataloged"
REASON_DISABLED = "capability.refused.disabled"
REASON_REAL_OPT_IN = "capability.refused.real_opt_in_required"
REASON_SCOPE = "capability.refused.scope_required"
REASON_REVIEW = "capability.refused.review_metadata_required"
REASON_DRY_RUN_ONLY = "capability.refused.dry_run_only"

ExecutionMode = Literal["denied", "stub", "dry_run", "real"]


class CatalogRefusal(Exception):
    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


@dataclass(frozen=True)
class CapabilityClassification:
    capability_id: str
    catalog_entry: CatalogEntry | None
    risk_class: str | None
    status: str | None
    execution_mode: ExecutionMode
    compensation_required: bool
    required_authority: tuple[str, ...]
    read_only: bool = True

    def to_payload(self) -> dict[str, Any]:
        return {
            "capability_id": self.capability_id,
            "cataloged": self.catalog_entry is not None,
            "risk_class": self.risk_class,
            "status": self.status,
            "execution_mode": self.execution_mode,
            "compensation_required": self.compensation_required,
            "required_authority": list(self.required_authority),
            "read_only": self.read_only,
        }


def _catalog(workspace: Path | None = None) -> CapabilityCatalog:
    return load_catalog(default_catalog_path(workspace))


def lookup_catalog_entry(
    capability_id: str,
    *,
    workspace: Path | None = None,
    catalog: CapabilityCatalog | None = None,
) -> CatalogEntry | None:
    cat = catalog or _catalog(workspace)
    return cat.lookup(capability_id)


def classify_capability(
    capability_id: str,
    *,
    workspace: Path | None = None,
    catalog: CapabilityCatalog | None = None,
    real_enabled: bool = False,
    allowed_capabilities: frozenset[str] | None = None,
) -> CapabilityClassification:
    """Read-only classification — does not mutate config or grant authority."""
    entry = lookup_catalog_entry(capability_id, workspace=workspace, catalog=catalog)
    if entry is None:
        return CapabilityClassification(
            capability_id=capability_id,
            catalog_entry=None,
            risk_class=None,
            status=None,
            execution_mode="denied",
            compensation_required=False,
            required_authority=(),
        )
    mode = effective_execution_mode(
        entry,
        real_enabled=real_enabled,
        allowed_capabilities=allowed_capabilities or frozenset(),
    )
    defaults = (catalog or _catalog(workspace)).class_defaults_for(entry.risk_class)
    compensation_required = entry.compensation_required or bool(
        defaults and defaults.compensation_required
    )
    authority = entry.required_authority or (defaults.required_authority if defaults else ())
    return CapabilityClassification(
        capability_id=capability_id,
        catalog_entry=entry,
        risk_class=entry.risk_class,
        status=entry.status,
        execution_mode=mode,
        compensation_required=compensation_required,
        required_authority=authority,
    )


def effective_execution_mode(
    entry: CatalogEntry,
    *,
    real_enabled: bool,
    allowed_capabilities: frozenset[str],
) -> ExecutionMode:
    if entry.status in {"disabled", "retired"}:
        return "denied"
    if entry.status == "stub":
        return "stub"
    if entry.status == "dry_run":
        return "dry_run"
    if entry.status == "real_gated":
        if not real_enabled:
            return "denied"
        if entry.capability_id not in allowed_capabilities and (
            not entry.oea_registry_id or entry.oea_registry_id not in allowed_capabilities
        ):
            return "denied"
        return "real"
    return "denied"


def validate_binding_authorization(
    entry: CatalogEntry,
    *,
    config: Any,
    review_metadata: Mapping[str, Any] | None = None,
    catalog: CapabilityCatalog | None = None,
) -> None:
    """Refuse bindings that violate catalog policy. Never enables OEA."""
    if entry.status in {"disabled", "retired"}:
        raise CatalogRefusal(REASON_DISABLED)
    real_enabled = bool(getattr(config, "is_real", False))
    allowed = frozenset(getattr(config, "allowed_capabilities", frozenset()))
    mode = effective_execution_mode(entry, real_enabled=real_enabled, allowed_capabilities=allowed)
    if mode == "denied":
        if entry.status == "real_gated" and not real_enabled:
            raise CatalogRefusal(REASON_REAL_OPT_IN)
        if entry.status == "real_gated":
            raise CatalogRefusal(REASON_SCOPE)
        raise CatalogRefusal(REASON_DISABLED)
    if entry.status == "dry_run" and real_enabled:
        raise CatalogRefusal(REASON_DRY_RUN_ONLY)
    if entry.risk_class in HIGH_REVIEW_RISK_CLASSES:
        required_tier = entry.min_review_tier
        cat = catalog or _catalog(None)
        defaults = cat.class_defaults_for(entry.risk_class)
        if defaults and _tier_rank(defaults.min_review_tier) > _tier_rank(required_tier):
            required_tier = defaults.min_review_tier
        actual_tier = (review_metadata or {}).get("review_tier")
        if not tier_meets(str(actual_tier) if actual_tier else None, required_tier):
            raise CatalogRefusal(REASON_REVIEW)


def _tier_rank(tier: str) -> int:
    from hg_core.capability_risk.catalog import REVIEW_TIERS

    order = {name: idx for idx, name in enumerate(REVIEW_TIERS)}
    return order.get(tier, -1)


def module_is_read_only(module_path: Path) -> bool:
    """Gate helper: ensure no authority-granting symbols in enforce module."""
    text = module_path.read_text(encoding="utf-8")
    marker = "def module_is_read_only"
    if marker in text:
        text = text.split(marker, 1)[0]
    forbidden = (
        "HG_OEA_REAL",
        "real_enabled=True",
        "os.environ",
        "enable_capability",
        "grant_authority",
    )
    return not any(token in text for token in forbidden)


__all__ = [
    "REASON_DISABLED",
    "REASON_DRY_RUN_ONLY",
    "REASON_REAL_OPT_IN",
    "REASON_REVIEW",
    "REASON_SCOPE",
    "REASON_UNCATALOGED",
    "CapabilityClassification",
    "CatalogRefusal",
    "classify_capability",
    "effective_execution_mode",
    "lookup_catalog_entry",
    "module_is_read_only",
    "validate_binding_authorization",
]
