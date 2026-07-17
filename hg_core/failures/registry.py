"""Reason code registry loader and validation (CT-05)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from hg_core.failures.types import ReasonCodeRecord, TerminalOutcome, ValidationResult

_REGISTRY_CACHE: "ReasonCodeRegistry | None" = None


def workspace_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_registry_path() -> Path:
    return workspace_root() / "config" / "reason_codes_v1.yaml"


def compute_registry_hash(payload: dict[str, Any]) -> str:
    from hg_srp.apply_types import content_hash

    body = {k: v for k, v in payload.items() if k != "registry_hash"}
    return content_hash({"reason_codes": body})


@dataclass(frozen=True)
class DynamicPattern:
    id: str
    regex: re.Pattern[str]
    canonical: str
    state: str


@dataclass(frozen=True)
class ReasonCodeRegistry:
    schema: str
    schema_version: str
    terminal_states: tuple[str, ...]
    precedence: tuple[str, ...]
    codes: tuple[ReasonCodeRecord, ...]
    dynamic_patterns: tuple[DynamicPattern, ...]
    incident_triggers: frozenset[str]
    legacy_alias_map: dict[str, str]
    code_index: dict[str, ReasonCodeRecord]
    registry_hash: str
    source_path: str

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "schema_version": self.schema_version,
            "terminal_states": list(self.terminal_states),
            "precedence": list(self.precedence),
            "codes": [code.to_payload() for code in self.codes],
            "incident_triggers": sorted(self.incident_triggers),
            "registry_hash": self.registry_hash,
        }


def load_registry(path: Path | None = None, *, use_cache: bool = True) -> ReasonCodeRegistry:
    global _REGISTRY_CACHE
    if use_cache and _REGISTRY_CACHE is not None and path is None:
        return _REGISTRY_CACHE

    reg_path = path or default_registry_path()
    raw = yaml.safe_load(reg_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or raw.get("schema") != "reason_codes_v1":
        raise ValueError("reason_codes_registry_invalid")

    terminal_states = tuple(str(s) for s in raw.get("terminal_states") or [])
    precedence = tuple(str(s) for s in raw.get("precedence") or [])
    incident_triggers = frozenset(str(s) for s in raw.get("incident_triggers") or [])

    codes: list[ReasonCodeRecord] = []
    legacy_alias_map: dict[str, str] = {}
    code_index: dict[str, ReasonCodeRecord] = {}

    for item in raw.get("codes") or []:
        record = ReasonCodeRecord(
            code=str(item["code"]),
            state=str(item["state"]),
            subsystem=str(item["subsystem"]),
            retryable=bool(item.get("retryable", False)),
            display_label=str(item.get("display_label") or item["code"]),
            legacy_aliases=tuple(str(a) for a in item.get("legacy_aliases") or []),
        )
        if record.state not in terminal_states:
            raise ValueError(f"unknown_terminal_state:{record.state}")
        codes.append(record)
        code_index[record.code] = record
        for alias in record.legacy_aliases:
            legacy_alias_map[alias] = record.code

    patterns: list[DynamicPattern] = []
    for item in raw.get("dynamic_patterns") or []:
        patterns.append(
            DynamicPattern(
                id=str(item["id"]),
                regex=re.compile(str(item["regex"])),
                canonical=str(item["canonical"]),
                state=str(item["state"]),
            )
        )

    payload = {
        "schema": raw["schema"],
        "schema_version": str(raw.get("schema_version") or "1.0"),
        "terminal_states": list(terminal_states),
        "precedence": list(precedence),
        "codes": [c.to_payload() for c in codes],
        "incident_triggers": sorted(incident_triggers),
    }
    registry_hash = compute_registry_hash(payload)

    registry = ReasonCodeRegistry(
        schema=str(raw["schema"]),
        schema_version=str(raw.get("schema_version") or "1.0"),
        terminal_states=terminal_states,
        precedence=precedence,
        codes=tuple(codes),
        dynamic_patterns=tuple(patterns),
        incident_triggers=incident_triggers,
        legacy_alias_map=legacy_alias_map,
        code_index=code_index,
        registry_hash=registry_hash,
        source_path=str(reg_path),
    )
    if use_cache and path is None:
        _REGISTRY_CACHE = registry
    return registry


def clear_registry_cache() -> None:
    global _REGISTRY_CACHE
    _REGISTRY_CACHE = None


def _resolve_reason(raw: str, registry: ReasonCodeRegistry) -> tuple[str, ReasonCodeRecord]:
    text = str(raw or "").strip()
    if not text:
        raise ValueError("empty_reason_code")
    if text in registry.code_index:
        return text, registry.code_index[text]
    if text in registry.legacy_alias_map:
        canonical = registry.legacy_alias_map[text]
        return canonical, registry.code_index[canonical]
    for pattern in registry.dynamic_patterns:
        match = pattern.regex.match(text)
        if not match:
            continue
        canonical = pattern.canonical.format(**match.groupdict()) if "{" in pattern.canonical else pattern.canonical
        if canonical in registry.code_index:
            return canonical, registry.code_index[canonical]
        subsystem = canonical.split(".", 1)[0]
        record = ReasonCodeRecord(
            code=canonical,
            state=pattern.state,
            subsystem=subsystem,
            retryable=False,
            display_label=canonical.replace(".", " "),
        )
        return canonical, record
    raise ValueError(f"unknown_reason_code:{text}")


def normalize_reason_code(raw: str, registry: ReasonCodeRegistry | None = None) -> str:
    reg = registry or load_registry()
    canonical, _ = _resolve_reason(raw, reg)
    return canonical


def validate_reason_code(raw: str, registry: ReasonCodeRegistry | None = None) -> ValidationResult:
    reg = registry or load_registry()
    try:
        canonical, record = _resolve_reason(raw, reg)
    except ValueError as exc:
        return ValidationResult(False, str(exc))
    return ValidationResult(True, "ok", canonical_code=canonical, record=record)


def terminal_state_for(raw: str, registry: ReasonCodeRegistry | None = None) -> str:
    result = validate_reason_code(raw, registry=registry)
    if not result.ok or result.record is None:
        raise ValueError(result.reason)
    return result.record.state


def display_label_for(raw: str, registry: ReasonCodeRegistry | None = None) -> str:
    result = validate_reason_code(raw, registry=registry)
    if not result.ok or result.record is None:
        return str(raw)
    return result.record.display_label


def terminal_outcome_from_reason(
    raw: str,
    *,
    incident_ref: str | None = None,
    registry: ReasonCodeRegistry | None = None,
) -> TerminalOutcome:
    result = validate_reason_code(raw, registry=registry)
    if not result.ok or result.record is None:
        raise ValueError(result.reason)
    return TerminalOutcome(
        state=result.record.state,
        reason_code=result.record.code,
        retryable=result.record.retryable,
        incident_ref=incident_ref,
    )


def validate_terminal_event(payload: dict[str, Any], registry: ReasonCodeRegistry | None = None) -> ValidationResult:
    reg = registry or load_registry()
    state = payload.get("state")
    reason = payload.get("reason_code")
    retryable = payload.get("retryable")
    if not state or not reason:
        return ValidationResult(False, "terminal_event_missing_fields")
    if state not in reg.terminal_states:
        return ValidationResult(False, f"unknown_terminal_state:{state}")
    if retryable is None:
        return ValidationResult(False, "retryable_required")
    code_result = validate_reason_code(str(reason), registry=reg)
    if not code_result.ok:
        return code_result
    if code_result.record and code_result.record.state != state:
        return ValidationResult(False, "state_reason_mismatch")
    return code_result


def legacy_migration_map(registry: ReasonCodeRegistry | None = None) -> dict[str, str]:
    reg = registry or load_registry()
    return dict(reg.legacy_alias_map)


__all__ = [
    "ReasonCodeRegistry",
    "clear_registry_cache",
    "compute_registry_hash",
    "default_registry_path",
    "display_label_for",
    "legacy_migration_map",
    "load_registry",
    "normalize_reason_code",
    "terminal_outcome_from_reason",
    "terminal_state_for",
    "validate_reason_code",
    "validate_terminal_event",
]
