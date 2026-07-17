"""Schema registry loader (CT-09 SCH)."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

ALLOWED_COMPAT = frozenset({"backward", "forward", "none"})
ALLOWED_STATUS = frozenset({"current", "deprecated", "retired"})
KNOWN_MANIFEST_SCHEMAS = frozenset(
    {
        "ct_proof_bundle_v1",
        "runtime_proof_bundle_v1",
        "path_parity_manifest_v1",
        "product_organism_bridge_manifest_v1",
        "reason_codes_v1",
        "truth_gate_registry_v1",
        "schema_registry_v1",
    }
)


@dataclass(frozen=True)
class SchemaEntry:
    schema_id: str
    version: int
    schema_ref: str
    content_hash: str | None
    compat: str
    reducer_version: int
    status: str
    since_commit: str
    manifest_schema: str | None = None

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> SchemaEntry:
        return cls(
            schema_id=str(raw["schema_id"]),
            version=int(raw["version"]),
            schema_ref=str(raw["schema_ref"]),
            content_hash=raw.get("content_hash"),
            compat=str(raw.get("compat", "none")),
            reducer_version=int(raw.get("reducer_version", 1)),
            status=str(raw.get("status", "current")),
            since_commit=str(raw.get("since_commit", "unknown")),
            manifest_schema=raw.get("manifest_schema"),
        )


@dataclass(frozen=True)
class CompatibilityRule:
    schema_id: str
    min_version: int
    max_version: int
    policy: str
    unknown_policy: str

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> CompatibilityRule:
        return cls(
            schema_id=str(raw["schema_id"]),
            min_version=int(raw["min_version"]),
            max_version=int(raw["max_version"]),
            policy=str(raw["policy"]),
            unknown_policy=str(raw.get("unknown_policy", "refuse")),
        )


@dataclass(frozen=True)
class GoldenFixture:
    fixture_id: str
    schema_id: str
    schema_version: int
    path: str
    expected_state_hash: str

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> GoldenFixture:
        return cls(
            fixture_id=str(raw["fixture_id"]),
            schema_id=str(raw["schema_id"]),
            schema_version=int(raw["schema_version"]),
            path=str(raw["path"]),
            expected_state_hash=str(raw["expected_state_hash"]),
        )


@dataclass(frozen=True)
class SchemaRegistry:
    schema: str
    registry_hash: str
    grandfather_rule: str
    schemas: tuple[SchemaEntry, ...]
    compatibility: tuple[CompatibilityRule, ...]
    golden_fixtures: tuple[GoldenFixture, ...]
    migrations: tuple[dict[str, Any], ...]

    def entry(self, schema_id: str, version: int) -> SchemaEntry | None:
        for item in self.schemas:
            if item.schema_id == schema_id and item.version == version:
                return item
        return None

    def entries_for(self, schema_id: str) -> tuple[SchemaEntry, ...]:
        return tuple(s for s in self.schemas if s.schema_id == schema_id)

    def compat_rule(self, schema_id: str) -> CompatibilityRule | None:
        for rule in self.compatibility:
            if rule.schema_id == schema_id:
                return rule
        return None

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "registry_hash": self.registry_hash,
            "grandfather_rule": self.grandfather_rule,
            "schemas": [
                {
                    "schema_id": s.schema_id,
                    "version": s.version,
                    "schema_ref": s.schema_ref,
                    "content_hash": s.content_hash,
                    "compat": s.compat,
                    "reducer_version": s.reducer_version,
                    "status": s.status,
                    "manifest_schema": s.manifest_schema,
                    "since_commit": s.since_commit,
                }
                for s in self.schemas
            ],
            "compatibility_matrix": [
                {
                    "schema_id": r.schema_id,
                    "min_version": r.min_version,
                    "max_version": r.max_version,
                    "policy": r.policy,
                    "unknown_policy": r.unknown_policy,
                }
                for r in self.compatibility
            ],
            "golden_fixtures": [
                {
                    "fixture_id": g.fixture_id,
                    "schema_id": g.schema_id,
                    "schema_version": g.schema_version,
                    "path": g.path,
                    "expected_state_hash": g.expected_state_hash,
                }
                for g in self.golden_fixtures
            ],
            "migrations": list(self.migrations),
        }


def default_registry_path(workspace: Path | None = None) -> Path:
    root = workspace or Path(__file__).resolve().parents[2]
    return root / "config" / "schema_registry.yaml"


def registry_hash(payload: dict[str, Any]) -> str:
    body = {k: v for k, v in payload.items() if k != "registry_hash"}
    raw = yaml.safe_dump(body, sort_keys=True, allow_unicode=True)
    return f"sha256:{hashlib.sha256(raw.encode('utf-8')).hexdigest()}"


def load_registry(path: Path | None = None, *, workspace: Path | None = None) -> SchemaRegistry:
    registry_path = path or default_registry_path(workspace)
    if not registry_path.exists():
        raise FileNotFoundError(f"schema registry missing: {registry_path}")
    payload = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("schema registry must be a mapping")
    schema = str(payload.get("schema", ""))
    if schema != "schema_registry_v1":
        raise ValueError(f"unsupported registry schema: {schema}")
    expected = payload.get("registry_hash")
    computed = registry_hash(payload)
    if expected and expected != "PLACEHOLDER" and expected != computed:
        raise ValueError(f"registry hash mismatch: expected {expected}, got {computed}")
    schemas_raw = payload.get("schemas", [])
    if not schemas_raw:
        raise ValueError("schema registry empty")
    seen: set[tuple[str, int]] = set()
    schemas: list[SchemaEntry] = []
    for raw in schemas_raw:
        entry = SchemaEntry.from_dict(raw)
        key = (entry.schema_id, entry.version)
        if key in seen:
            raise ValueError(f"duplicate schema entry: {key}")
        seen.add(key)
        if entry.compat not in ALLOWED_COMPAT:
            raise ValueError(f"invalid compat for {entry.schema_id}: {entry.compat}")
        if entry.status not in ALLOWED_STATUS:
            raise ValueError(f"invalid status for {entry.schema_id}: {entry.status}")
        schemas.append(entry)
    compatibility = tuple(CompatibilityRule.from_dict(r) for r in payload.get("compatibility_matrix", []))
    golden = tuple(GoldenFixture.from_dict(g) for g in payload.get("golden_fixtures", []))
    migrations = tuple(payload.get("migrations", []))
    return SchemaRegistry(
        schema=schema,
        registry_hash=computed,
        grandfather_rule=str(payload.get("grandfather_rule", "")),
        schemas=tuple(schemas),
        compatibility=compatibility,
        golden_fixtures=golden,
        migrations=migrations,
    )


__all__ = [
    "ALLOWED_STATUS",
    "GoldenFixture",
    "KNOWN_MANIFEST_SCHEMAS",
    "SchemaEntry",
    "SchemaRegistry",
    "default_registry_path",
    "load_registry",
    "registry_hash",
]
