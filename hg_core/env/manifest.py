"""Environment manifest loader (CT-16 ENV)."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class EnvVarSpec:
    name: str
    feature: str
    tier: str = "optional"
    required: bool = False

    @classmethod
    def from_dict(cls, raw: dict[str, Any], *, required: bool = False) -> EnvVarSpec:
        return cls(
            name=str(raw["name"]),
            feature=str(raw.get("feature", "unknown")),
            tier=str(raw.get("tier", "required" if required else "optional")),
            required=required,
        )


@dataclass(frozen=True)
class EnvManifest:
    schema: str
    manifest_hash: str
    authority_note: str
    python_min: str
    python_max: str
    python_impl: str
    package_lock_path: str
    package_lock_hash: str
    timezone: str
    offline_env_flag: str
    offline_baseline_allowed: bool
    required_modules: tuple[str, ...]
    required_env_vars: tuple[EnvVarSpec, ...]
    optional_env_vars: tuple[EnvVarSpec, ...]
    gated_env_vars: tuple[EnvVarSpec, ...]
    baseline_commands: tuple[str, ...]
    setup_scripts: tuple[str, ...]
    os_dev: tuple[str, ...]
    os_deploy: tuple[str, ...]

    def all_env_vars(self) -> tuple[EnvVarSpec, ...]:
        return self.required_env_vars + self.optional_env_vars + self.gated_env_vars


def default_manifest_path(workspace: Path | None = None) -> Path:
    root = workspace or Path(__file__).resolve().parents[2]
    return root / "config" / "env_manifest_v1.yaml"


def manifest_hash(payload: dict[str, Any]) -> str:
    body = {k: v for k, v in payload.items() if k != "manifest_hash"}
    raw = yaml.safe_dump(body, sort_keys=True, allow_unicode=True)
    return f"sha256:{hashlib.sha256(raw.encode('utf-8')).hexdigest()}"


def load_manifest(path: Path | None = None, *, workspace: Path | None = None) -> EnvManifest:
    manifest_path = path or default_manifest_path(workspace)
    if not manifest_path.exists():
        raise FileNotFoundError(f"env manifest missing: {manifest_path}")
    payload = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    schema = str(payload.get("schema", ""))
    if schema != "env_manifest_v1":
        raise ValueError(f"unsupported env manifest schema: {schema}")
    expected = payload.get("manifest_hash")
    computed = manifest_hash(payload)
    if expected and expected != computed:
        raise ValueError(f"env manifest hash mismatch: expected {expected}, got {computed}")
    python = payload.get("python", {})
    lock = payload.get("package_lock", {})
    offline = payload.get("offline_mode", {})
    os_support = payload.get("os_support", {})
    return EnvManifest(
        schema=schema,
        manifest_hash=computed,
        authority_note=str(payload.get("authority_note", "")),
        python_min=str(python.get("min_version", "3.10")),
        python_max=str(python.get("max_version", "3.14")),
        python_impl=str(python.get("implementation", "cpython")),
        package_lock_path=str(lock.get("path", "requirements-frozen.txt")),
        package_lock_hash=str(lock.get("hash", "")),
        timezone=str(payload.get("timezone", "UTC")),
        offline_env_flag=str(offline.get("env_flag", "HG_NO_NETWORK")),
        offline_baseline_allowed=bool(offline.get("baseline_allowed", True)),
        required_modules=tuple(str(x) for x in payload.get("required_modules", ())),
        required_env_vars=tuple(
            EnvVarSpec.from_dict(item, required=True) for item in payload.get("required_env_vars", ())
        ),
        optional_env_vars=tuple(
            EnvVarSpec.from_dict(item) for item in payload.get("optional_env_vars", ())
        ),
        gated_env_vars=tuple(EnvVarSpec.from_dict(item) for item in payload.get("gated_env_vars", ())),
        baseline_commands=tuple(str(x) for x in payload.get("baseline_commands", ())),
        setup_scripts=tuple(str(x) for x in payload.get("setup_scripts", ())),
        os_dev=tuple(str(x) for x in os_support.get("dev", ())),
        os_deploy=tuple(str(x) for x in os_support.get("deploy", ())),
    )


__all__ = ["EnvManifest", "EnvVarSpec", "default_manifest_path", "load_manifest", "manifest_hash"]
