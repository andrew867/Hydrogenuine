"""OEA capability risk catalog loader (CT-12 CAP)."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import yaml

RISK_CLASSES = (
    "harmless_local",
    "guarded",
    "sensitive",
    "irreversible",
    "external",
    "physical_future",
)

CAPABILITY_STATUSES = (
    "disabled",
    "dry_run",
    "stub",
    "real_gated",
    "retired",
)

REVIEW_TIERS = ("none", "standard", "elevated", "high_risk", "high_risk_plus_confirmation")

HIGH_REVIEW_RISK_CLASSES = frozenset({"irreversible", "external", "physical_future"})


@dataclass(frozen=True)
class ClassDefaults:
    risk_class: str
    required_evidence: tuple[str, ...]
    required_authority: tuple[str, ...]
    compensation_required: bool
    min_review_tier: str

    @classmethod
    def from_dict(cls, risk_class: str, raw: Mapping[str, Any]) -> ClassDefaults:
        return cls(
            risk_class=risk_class,
            required_evidence=tuple(str(x) for x in raw.get("required_evidence", ())),
            required_authority=tuple(str(x) for x in raw.get("required_authority", ())),
            compensation_required=bool(raw.get("compensation_required", False)),
            min_review_tier=str(raw.get("min_review_tier", "none")),
        )


@dataclass(frozen=True)
class CatalogEntry:
    capability_id: str
    name: str
    description: str
    risk_class: str
    status: str
    dry_run_mode: str
    compensation: str
    compensation_required: bool
    drill_ref: str | None
    required_evidence: tuple[str, ...]
    required_authority: tuple[str, ...]
    min_review_tier: str
    oea_registry_id: str | None = None
    hazard_note: str = ""
    plt_display: str = "badge_only"
    concurrency_limit: int = 1

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> CatalogEntry:
        return cls(
            capability_id=str(raw["capability_id"]),
            name=str(raw.get("name", raw["capability_id"])),
            description=str(raw.get("description", "")),
            risk_class=str(raw["risk_class"]),
            status=str(raw["status"]),
            dry_run_mode=str(raw.get("dry_run_mode", "not_applicable")),
            compensation=str(raw.get("compensation", "none")),
            compensation_required=bool(raw.get("compensation_required", False)),
            drill_ref=raw.get("drill_ref"),
            required_evidence=tuple(str(x) for x in raw.get("required_evidence", ())),
            required_authority=tuple(str(x) for x in raw.get("required_authority", ())),
            min_review_tier=str(raw.get("min_review_tier", "none")),
            oea_registry_id=raw.get("oea_registry_id"),
            hazard_note=str(raw.get("hazard_note", "")),
            plt_display=str(raw.get("plt_display", "badge_only")),
            concurrency_limit=int(raw.get("concurrency_limit", 1)),
        )

    def to_payload(self) -> dict[str, Any]:
        return {
            "capability_id": self.capability_id,
            "name": self.name,
            "description": self.description,
            "risk_class": self.risk_class,
            "status": self.status,
            "dry_run_mode": self.dry_run_mode,
            "compensation": self.compensation,
            "compensation_required": self.compensation_required,
            "drill_ref": self.drill_ref,
            "required_evidence": list(self.required_evidence),
            "required_authority": list(self.required_authority),
            "min_review_tier": self.min_review_tier,
            "oea_registry_id": self.oea_registry_id,
            "hazard_note": self.hazard_note,
            "plt_display": self.plt_display,
            "concurrency_limit": self.concurrency_limit,
        }


CapabilityEntry = CatalogEntry


@dataclass(frozen=True)
class CapabilityCatalog:
    schema: str
    catalog_hash: str
    authority_note: str
    risk_classes: tuple[str, ...]
    capability_statuses: tuple[str, ...]
    class_defaults: dict[str, ClassDefaults]
    capabilities: tuple[CatalogEntry, ...]

    def lookup(self, capability_id: str) -> CatalogEntry | None:
        for entry in self.capabilities:
            if entry.capability_id == capability_id:
                return entry
            if entry.oea_registry_id == capability_id:
                return entry
        return None

    def class_defaults_for(self, risk_class: str) -> ClassDefaults | None:
        return self.class_defaults.get(risk_class)

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "catalog_hash": self.catalog_hash,
            "authority_note": self.authority_note,
            "risk_classes": list(self.risk_classes),
            "capability_statuses": list(self.capability_statuses),
            "class_defaults": {
                k: {
                    "required_evidence": list(v.required_evidence),
                    "required_authority": list(v.required_authority),
                    "compensation_required": v.compensation_required,
                    "min_review_tier": v.min_review_tier,
                }
                for k, v in self.class_defaults.items()
            },
            "capabilities": [c.to_payload() for c in self.capabilities],
        }


def default_catalog_path(workspace: Path | None = None) -> Path:
    root = workspace or Path(__file__).resolve().parents[2]
    return root / "config" / "oea_capability_risk_catalog_v1.yaml"


def catalog_hash(payload: dict[str, Any]) -> str:
    body = {k: v for k, v in payload.items() if k != "catalog_hash"}
    raw = yaml.safe_dump(body, sort_keys=True, allow_unicode=True)
    return f"sha256:{hashlib.sha256(raw.encode('utf-8')).hexdigest()}"


def _tier_rank(tier: str) -> int:
    order = {name: idx for idx, name in enumerate(REVIEW_TIERS)}
    return order.get(tier, -1)


def tier_meets(actual: str | None, required: str) -> bool:
    if required == "none":
        return True
    if not actual:
        return False
    return _tier_rank(actual) >= _tier_rank(required)


def _validate_entry(entry: CatalogEntry, defaults: ClassDefaults) -> None:
    if entry.risk_class not in RISK_CLASSES:
        raise ValueError(f"unknown risk_class for {entry.capability_id}: {entry.risk_class}")
    if entry.status not in CAPABILITY_STATUSES:
        raise ValueError(f"unknown status for {entry.capability_id}: {entry.status}")
    if entry.risk_class == "physical_future" and not entry.hazard_note:
        raise ValueError(f"physical_future entry requires hazard_note: {entry.capability_id}")
    if entry.compensation == "none" and entry.compensation_required:
        if _tier_rank(entry.min_review_tier) < _tier_rank("high_risk"):
            raise ValueError(
                f"compensation none requires min_review_tier >= high_risk: {entry.capability_id}"
            )
    if entry.compensation_required and entry.compensation != "none" and not entry.drill_ref:
        raise ValueError(f"compensation_required entry needs drill_ref: {entry.capability_id}")
    if entry.risk_class in HIGH_REVIEW_RISK_CLASSES:
        required = entry.min_review_tier or defaults.min_review_tier
        if _tier_rank(required) < _tier_rank("elevated"):
            raise ValueError(
                f"{entry.risk_class} capability requires elevated review tier: {entry.capability_id}"
            )
    if entry.status not in {"disabled", "retired", "stub"} and entry.risk_class in {
        "guarded",
        "sensitive",
        "irreversible",
        "external",
        "physical_future",
    }:
        if entry.status not in {"disabled", "retired"}:
            pass  # enabled high-risk must be explicitly real_gated or dry_run with review


def load_catalog(path: Path | None = None, *, workspace: Path | None = None) -> CapabilityCatalog:
    catalog_path = path or default_catalog_path(workspace)
    if not catalog_path.exists():
        raise FileNotFoundError(f"capability catalog missing: {catalog_path}")
    payload = yaml.safe_load(catalog_path.read_text(encoding="utf-8"))
    schema = str(payload.get("schema", ""))
    if schema != "oea_capability_risk_catalog_v1":
        raise ValueError(f"unsupported catalog schema: {schema}")
    expected = payload.get("catalog_hash")
    computed = catalog_hash(payload)
    if expected and expected != "PLACEHOLDER" and expected != computed:
        raise ValueError(f"catalog hash mismatch: expected {expected}, got {computed}")
    risk_classes = tuple(str(x) for x in payload.get("risk_classes", ()))
    if set(risk_classes) != set(RISK_CLASSES):
        raise ValueError(f"risk_classes must be closed set: {risk_classes}")
    statuses = tuple(str(x) for x in payload.get("capability_statuses", ()))
    if set(statuses) != set(CAPABILITY_STATUSES):
        raise ValueError(f"capability_statuses must be closed set: {statuses}")
    defaults_raw = payload.get("class_defaults", {})
    class_defaults = {
        str(k): ClassDefaults.from_dict(str(k), v) for k, v in defaults_raw.items()
    }
    if set(class_defaults) != set(RISK_CLASSES):
        raise ValueError("class_defaults must cover every risk_class")
    capabilities = tuple(CatalogEntry.from_dict(c) for c in payload.get("capabilities", ()))
    for entry in capabilities:
        defaults = class_defaults[entry.risk_class]
        _validate_entry(entry, defaults)
    return CapabilityCatalog(
        schema=schema,
        catalog_hash=computed,
        authority_note=str(payload.get("authority_note", "")),
        risk_classes=risk_classes,
        capability_statuses=statuses,
        class_defaults=class_defaults,
        capabilities=capabilities,
    )


__all__ = [
    "CAPABILITY_STATUSES",
    "HIGH_REVIEW_RISK_CLASSES",
    "REVIEW_TIERS",
    "RISK_CLASSES",
    "CapabilityCatalog",
    "CapabilityEntry",
    "CatalogEntry",
    "ClassDefaults",
    "catalog_hash",
    "default_catalog_path",
    "load_catalog",
    "tier_meets",
]
