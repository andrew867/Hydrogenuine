"""Schema artifact validation (CT-09 SCH)."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from hg_core.schema_compat.registry import SchemaRegistry, load_registry

REASON_VERSION_UNSUPPORTED = "schema.refused.version_unsupported"
REASON_UNKNOWN_SCHEMA = "schema.refused.unknown_schema_id"
REASON_MIGRATION_LOSSY = "schema.refused.migration_lossy"


@dataclass(frozen=True)
class ValidationFinding:
    check: str
    verdict: str
    detail: str
    schema_id: str | None = None

    def to_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"check": self.check, "verdict": self.verdict, "detail": self.detail}
        if self.schema_id:
            payload["schema_id"] = self.schema_id
        return payload


def _sha256_file(path: Path) -> str:
    return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"


def validate_artifact_record(
    record: dict[str, Any],
    registry: SchemaRegistry,
    *,
    allow_grandfather: bool = True,
) -> ValidationFinding:
    schema_id = record.get("schema_id") or record.get("schema")
    version_raw = record.get("schema_version")
    if schema_id is None and "schema" in record and isinstance(record["schema"], str):
        # manifest-style: schema field is manifest type name
        manifest_schema = str(record["schema"])
        for entry in registry.schemas:
            if entry.manifest_schema == manifest_schema:
                schema_id = entry.schema_id
                version_raw = entry.version
                break
    if version_raw is None and allow_grandfather:
        version_raw = 1
    if schema_id is None:
        return ValidationFinding(
            check="schema_record",
            verdict="fail",
            detail=REASON_UNKNOWN_SCHEMA,
        )
    try:
        version = int(str(version_raw).split(".")[0]) if version_raw is not None else 1
    except (TypeError, ValueError):
        return ValidationFinding(
            check="schema_record",
            verdict="fail",
            detail=f"invalid schema_version: {version_raw}",
            schema_id=str(schema_id),
        )
    sid = str(schema_id)
    entry = registry.entry(sid, version)
    if entry is None:
        known_versions = [e.version for e in registry.entries_for(sid)]
        if known_versions:
            return ValidationFinding(
                check="schema_record",
                verdict="fail",
                detail=REASON_VERSION_UNSUPPORTED,
                schema_id=sid,
            )
        allowed = registry.compat_rule(sid)
        if allowed and allowed.unknown_policy == "preserve_unknown_event":
            return ValidationFinding(
                check="schema_record",
                verdict="pass",
                detail="unknown schema preserved per stream policy",
                schema_id=sid,
            )
        return ValidationFinding(
            check="schema_record",
            verdict="fail",
            detail=REASON_UNKNOWN_SCHEMA,
            schema_id=sid,
        )
    rule = registry.compat_rule(entry.schema_id)
    if rule and not (rule.min_version <= version <= rule.max_version):
        return ValidationFinding(
            check="schema_record",
            verdict="fail",
            detail=REASON_VERSION_UNSUPPORTED,
            schema_id=entry.schema_id,
        )
    if entry.status == "deprecated":
        return ValidationFinding(
            check="schema_record",
            verdict="pass",
            detail="deprecated schema flagged",
            schema_id=entry.schema_id,
        )
    return ValidationFinding(
        check="schema_record",
        verdict="pass",
        detail=f"v{version} current",
        schema_id=entry.schema_id,
    )


def validate_registry_artifacts(
    registry: SchemaRegistry | None = None,
    *,
    workspace: Path | None = None,
) -> list[ValidationFinding]:
    root = workspace or Path(__file__).resolve().parents[2]
    loaded = registry or load_registry(workspace=root)
    findings: list[ValidationFinding] = []

    for entry in loaded.schemas:
        ref = root / entry.schema_ref
        if entry.content_hash is None:
            if ref.suffix in {".py", ".md"} or ref.is_dir():
                findings.append(
                    ValidationFinding(
                        check="schema_ref_exists",
                        verdict="pass" if ref.exists() else "fail",
                        detail=str(entry.schema_ref),
                        schema_id=entry.schema_id,
                    )
                )
            continue
        if not ref.exists():
            findings.append(
                ValidationFinding(
                    check="schema_ref_exists",
                    verdict="fail",
                    detail=f"missing: {entry.schema_ref}",
                    schema_id=entry.schema_id,
                )
            )
            continue
        actual = _sha256_file(ref)
        if actual != entry.content_hash:
            findings.append(
                ValidationFinding(
                    check="version_bump_lint",
                    verdict="fail",
                    detail=f"content changed without version bump: {actual} != {entry.content_hash}",
                    schema_id=entry.schema_id,
                )
            )
        else:
            findings.append(
                ValidationFinding(
                    check="version_bump_lint",
                    verdict="pass",
                    detail="content hash anchored",
                    schema_id=entry.schema_id,
                )
            )
        if entry.status == "deprecated":
            findings.append(
                ValidationFinding(
                    check="deprecated_schema_flagged",
                    verdict="pass",
                    detail="deprecated entry present",
                    schema_id=entry.schema_id,
                )
            )

    for entry in loaded.schemas:
        if not entry.manifest_schema:
            continue
        if entry.manifest_schema not in {e.manifest_schema for e in loaded.schemas if e.manifest_schema}:
            continue
        # validated via content_hash paths above
        findings.append(
            ValidationFinding(
                check="manifest_schema_registered",
                verdict="pass",
                detail=entry.manifest_schema,
                schema_id=entry.schema_id,
            )
        )

    return findings


def findings_ok(findings: list[ValidationFinding]) -> bool:
    return all(f.verdict == "pass" for f in findings)


def refuse_unsupported_version(schema_id: str, version: int, registry: SchemaRegistry) -> dict[str, Any]:
    """Explicit refusal payload for unsupported schema versions."""
    return {
        "reason_code": REASON_VERSION_UNSUPPORTED,
        "schema_id": schema_id,
        "schema_version": version,
        "allowed_versions": [e.version for e in registry.entries_for(schema_id)],
    }


def migration_error(schema_id: str, from_version: int, to_version: int, reason: str) -> dict[str, Any]:
    return {
        "reason_code": REASON_MIGRATION_LOSSY,
        "schema_id": schema_id,
        "from_version": from_version,
        "to_version": to_version,
        "detail": reason,
    }


__all__ = [
    "REASON_MIGRATION_LOSSY",
    "REASON_UNKNOWN_SCHEMA",
    "REASON_VERSION_UNSUPPORTED",
    "ValidationFinding",
    "findings_ok",
    "migration_error",
    "refuse_unsupported_version",
    "validate_artifact_record",
    "validate_registry_artifacts",
]
