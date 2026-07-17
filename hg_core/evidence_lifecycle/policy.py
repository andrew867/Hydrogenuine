"""Retention policy manifest loader (CT-10 RET)."""

from __future__ import annotations

import hashlib
import fnmatch
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

REQUIRED_CLASSES = (
    "proof",
    "receipt",
    "log",
    "report",
    "temp",
    "sensitive",
    "external_receipt",
)

CLOSED_TIERS = frozenset(
    {"immutable", "append_only", "compactable", "archivable", "temporary", "sensitive"}
)


@dataclass(frozen=True)
class ArtifactClassPolicy:
    artifact_class: str
    tier: str
    owner_subsystem: str
    min_retention_days: int | None = None
    ttl_hours: int | None = None
    export_requires_manifest: bool = False
    export_requires_hashes: bool = False
    gate_minimum: bool = False
    sec_handling_required: bool = False
    redaction_before_export: bool = False
    notes: str = ""

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> ArtifactClassPolicy:
        return cls(
            artifact_class=str(raw["class"]),
            tier=str(raw["tier"]),
            owner_subsystem=str(raw["owner_subsystem"]),
            min_retention_days=raw.get("min_retention_days"),
            ttl_hours=raw.get("ttl_hours"),
            export_requires_manifest=bool(raw.get("export_requires_manifest", False)),
            export_requires_hashes=bool(raw.get("export_requires_hashes", False)),
            gate_minimum=bool(raw.get("gate_minimum", False)),
            sec_handling_required=bool(raw.get("sec_handling_required", False)),
            redaction_before_export=bool(raw.get("redaction_before_export", False)),
            notes=str(raw.get("notes", "")),
        )


@dataclass(frozen=True)
class PathClassRule:
    pattern: str
    artifact_class: str


@dataclass(frozen=True)
class RetentionPolicy:
    schema: str
    policy_hash: str
    authority_note: str
    tiers: tuple[str, ...]
    artifact_classes: tuple[ArtifactClassPolicy, ...]
    path_rules: tuple[PathClassRule, ...]
    minimum_retention: dict[str, Any]

    def class_policy(self, artifact_class: str) -> ArtifactClassPolicy | None:
        for entry in self.artifact_classes:
            if entry.artifact_class == artifact_class:
                return entry
        return None

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "policy_hash": self.policy_hash,
            "authority_note": self.authority_note,
            "tiers": list(self.tiers),
            "artifact_classes": [
                {
                    "class": c.artifact_class,
                    "tier": c.tier,
                    "owner_subsystem": c.owner_subsystem,
                    "min_retention_days": c.min_retention_days,
                    "ttl_hours": c.ttl_hours,
                    "export_requires_manifest": c.export_requires_manifest,
                    "export_requires_hashes": c.export_requires_hashes,
                    "gate_minimum": c.gate_minimum,
                    "sec_handling_required": c.sec_handling_required,
                    "redaction_before_export": c.redaction_before_export,
                    "notes": c.notes,
                }
                for c in self.artifact_classes
            ],
            "path_class_rules": [{"pattern": r.pattern, "class": r.artifact_class} for r in self.path_rules],
            "minimum_retention": self.minimum_retention,
        }


def default_policy_path(workspace: Path | None = None) -> Path:
    root = workspace or Path(__file__).resolve().parents[2]
    return root / "config" / "retention_policy_v1.yaml"


def policy_hash(payload: dict[str, Any]) -> str:
    body = {k: v for k, v in payload.items() if k != "policy_hash"}
    raw = yaml.safe_dump(body, sort_keys=True, allow_unicode=True)
    return f"sha256:{hashlib.sha256(raw.encode('utf-8')).hexdigest()}"


def load_policy(path: Path | None = None, *, workspace: Path | None = None) -> RetentionPolicy:
    policy_path = path or default_policy_path(workspace)
    if not policy_path.exists():
        raise FileNotFoundError(f"retention policy missing: {policy_path}")
    payload = yaml.safe_load(policy_path.read_text(encoding="utf-8"))
    schema = str(payload.get("schema", ""))
    if schema != "retention_policy_v1":
        raise ValueError(f"unsupported policy schema: {schema}")
    expected = payload.get("policy_hash")
    computed = policy_hash(payload)
    if expected and expected != "PLACEHOLDER" and expected != computed:
        raise ValueError(f"policy hash mismatch: expected {expected}, got {computed}")
    tiers = tuple(payload.get("tiers", []))
    if set(tiers) != CLOSED_TIERS:
        raise ValueError(f"tier set must be closed: {tiers}")
    classes_raw = payload.get("artifact_classes", [])
    found = {str(c["class"]) for c in classes_raw}
    missing = [name for name in REQUIRED_CLASSES if name not in found]
    if missing:
        raise ValueError(f"missing artifact classes: {missing}")
    classes = tuple(ArtifactClassPolicy.from_dict(c) for c in classes_raw)
    for entry in classes:
        if entry.tier not in CLOSED_TIERS:
            raise ValueError(f"invalid tier for {entry.artifact_class}: {entry.tier}")
    rules = tuple(
        PathClassRule(pattern=str(r["pattern"]), artifact_class=str(r["class"]))
        for r in payload.get("path_class_rules", [])
    )
    return RetentionPolicy(
        schema=schema,
        policy_hash=computed,
        authority_note=str(payload.get("authority_note", "")),
        tiers=tiers,
        artifact_classes=classes,
        path_rules=rules,
        minimum_retention=dict(payload.get("minimum_retention", {})),
    )


def classify_path(path: str | Path, policy: RetentionPolicy) -> str | None:
    normalized = str(path).replace("\\", "/")
    for rule in policy.path_rules:
        if fnmatch.fnmatch(normalized, rule.pattern):
            return rule.artifact_class
    return None


__all__ = [
    "CLOSED_TIERS",
    "ArtifactClassPolicy",
    "PathClassRule",
    "REQUIRED_CLASSES",
    "RetentionPolicy",
    "classify_path",
    "default_policy_path",
    "load_policy",
    "policy_hash",
]
