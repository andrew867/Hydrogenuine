"""Temporal Experience Readiness schema."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

FROZEN_FALSE = {
    "advisory_only": True,
    "permission_granted": False,
    "authority_created": False,
}


class FeatureClassification(str, Enum):
    REQUIRED_NOW_COMPLETE = "REQUIRED_NOW_COMPLETE"
    REQUIRED_NOW_BLOCKER = "REQUIRED_NOW_BLOCKER"
    REQUIRED_NOW_TEST_GAP = "REQUIRED_NOW_TEST_GAP"
    REQUIRED_NOW_DOC_GAP = "REQUIRED_NOW_DOC_GAP"
    REQUIRED_NOW_BOOT_WIRING_GAP = "REQUIRED_NOW_BOOT_WIRING_GAP"
    REQUIRED_NOW_GATE_REGISTRY_GAP = "REQUIRED_NOW_GATE_REGISTRY_GAP"
    FUTURE_WORK_ITEM = "FUTURE_WORK_ITEM"
    DUPLICATE_OR_SUPERSEDED = "DUPLICATE_OR_SUPERSEDED"
    INVALID_OR_STALE = "INVALID_OR_STALE"


class TemporalReadinessVerdict(str, Enum):
    GREEN_TEMPORAL_EXPERIENCE_READY = "GREEN_TEMPORAL_EXPERIENCE_READY"
    YELLOW_LIVE_ANCHOR_NOT_PUSHED = "YELLOW_LIVE_ANCHOR_NOT_PUSHED"
    YELLOW_AUDIO_PLAYBACK_DISABLED = "YELLOW_AUDIO_PLAYBACK_DISABLED"
    YELLOW_LIVE_WEATHER_DISABLED = "YELLOW_LIVE_WEATHER_DISABLED"
    RED_REQUIRED_SLICE_DEFERRED = "RED_REQUIRED_SLICE_DEFERRED"
    RED_FEATURE_NOT_DISCOVERABLE = "RED_FEATURE_NOT_DISCOVERABLE"
    RED_BOOT_CONTEXT_MISSING = "RED_BOOT_CONTEXT_MISSING"
    RED_GATE_ORPHAN = "RED_GATE_ORPHAN"
    RED_SECRET_LEAK = "RED_SECRET_LEAK"
    RED_AUTHORITY_CONVERSION = "RED_AUTHORITY_CONVERSION"
    RED_LIVE_SIDE_EFFECT = "RED_LIVE_SIDE_EFFECT"


@dataclass
class TemporalFeatureStatus:
    module_id: str
    classification: FeatureClassification
    package_path: str = ""
    boot_attached: bool = False
    self_mirror_discoverable: bool = False
    gate_registered: bool = False
    default_enabled: bool = False
    last_verdict: str = ""
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "module_id": self.module_id,
            "classification": self.classification.value,
            "package_path": self.package_path,
            "boot_attached": self.boot_attached,
            "self_mirror_discoverable": self.self_mirror_discoverable,
            "gate_registered": self.gate_registered,
            "default_enabled": self.default_enabled,
            "last_verdict": self.last_verdict,
            "notes": self.notes,
        }


@dataclass
class BootContextCompleteness:
    required_keys: list[str]
    present_keys: list[str]
    missing_keys: list[str]
    complete: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "required_keys": self.required_keys,
            "present_keys": self.present_keys,
            "missing_keys": self.missing_keys,
            "complete": self.complete,
        }


@dataclass
class DefaultSafetyMatrix:
    safe_defaults_on: list[str] = field(default_factory=list)
    dangerous_defaults_off: list[str] = field(default_factory=list)
    violations: list[str] = field(default_factory=list)
    ok: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "safe_defaults_on": self.safe_defaults_on,
            "dangerous_defaults_off": self.dangerous_defaults_off,
            "violations": self.violations,
            "ok": self.ok,
        }


@dataclass
class RequiredSliceInventory:
    features: list[TemporalFeatureStatus] = field(default_factory=list)

    @property
    def required_now_remaining(self) -> list[TemporalFeatureStatus]:
        return [f for f in self.features if f.classification.value.startswith("REQUIRED_NOW_") and f.classification != FeatureClassification.REQUIRED_NOW_COMPLETE]

    def to_dict(self) -> dict[str, Any]:
        return {
            "features": [f.to_dict() for f in self.features],
            "required_now_remaining": [f.module_id for f in self.required_now_remaining],
        }


@dataclass
class TemporalExperienceReadinessReport:
    verdict: str
    boot_completeness: BootContextCompleteness
    defaults: DefaultSafetyMatrix
    inventory: RequiredSliceInventory
    failures: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema": "temporal-experience-readiness-report",
            "verdict": self.verdict,
            "boot_completeness": self.boot_completeness.to_dict(),
            "defaults": self.defaults.to_dict(),
            "inventory": self.inventory.to_dict(),
            "failures": self.failures,
            "warnings": self.warnings,
            **FROZEN_FALSE,
        }


__all__ = [
    "BootContextCompleteness",
    "DefaultSafetyMatrix",
    "FeatureClassification",
    "RequiredSliceInventory",
    "TemporalExperienceReadinessReport",
    "TemporalFeatureStatus",
    "TemporalReadinessVerdict",
]
